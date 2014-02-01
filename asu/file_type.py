import os
import sys
import re
from collections import namedtuple

from . import (DEFAULT_OUTPUT_FILE_TYPE, DEFAULT_SCREENSHOT_FILE_EXTENSION,
               DEFAULT_FFMPEG_COMMAND)
from . import markup
from .utils import qoute_path, run_command, regex_in_string

Timecode = namedtuple('Timecode', "string, seconds")


class AsuFile(object):
    def __init__(self, path):
        from os.path import abspath, basename, splitext

        self.path = path
        self.abspath = abspath(path) if self.exists() else None

        self.filename = basename(path)
        self.ext = splitext(path)[1].strip('.')

    def exists(self):
        return os.path.isfile(self.path)


class InputFile(AsuFile):
    duration = Timecode(None, None)

    def __init__(self, path):
        super(InputFile, self).__init__(path)

        self.screenshots = []

    def __repr__(self):
        if self.screenshots:
            fmt = "InputFile({}, {}, {} screenshot{})"
            n = len(self.screenshots)
            return fmt.format(self.path, self.get_duration().string, n,
                              "s" if n > 1 else "")
        else:
            return "InputFile({}, {})".format(self.path,
                                              self.get_duration().string)

    def get_duration(self, ffmpeg=None):
        ffmpeg = ffmpeg or DEFAULT_FFMPEG_COMMAND

        if self.duration != (None, None):
            return self.duration

        if 'win32' in sys.platform:
            path = qoute_path(self.path)
        else:
            path = self.path

        _, _, stderr = run_command(ffmpeg, '-i', path)

        regex = re.compile(r'(?<=(Timecode|Duration):\s)\d\d?:\d\d:\d\d(?=\.)')
        dur_string = regex_in_string(regex, stderr.decode())
        if not dur_string:
            return None

        elems = dur_string.split(':')
        dur_seconds = (int(elems[0]) * 60 * 60 + int(elems[1]) * 60 +
                       int(elems[2]))

        self.duration = Timecode(dur_string, dur_seconds)

        return self.duration

    def make_screenshot(self, path, timecode, ffmpeg=None,
                        frame_accurate=False, extra_args=None):
        ffmpeg = ffmpeg or DEFAULT_FFMPEG_COMMAND

        args = ['-y']

        if frame_accurate:
            if timecode > 30:
                args += ['-ss', str(timecode - 30)]
        else:
            args += ['-ss', str(timecode)]

        args.append('-i')
        if 'win32' in sys.platform:
            args.append(qoute_path(self.path))
        else:
            args.append(self.path)

        if frame_accurate:
            args += ['-ss', "30" if timecode > 30 else str(timecode)]

        args += ['-vframes', '1', '-vcodec', DEFAULT_OUTPUT_FILE_TYPE]

        if 'win32' in sys.platform:
            if extra_args:
                args.append(extra_args)
            args.append(qoute_path(path))
        else:
            if extra_args:
                args += extra_args.split(' ')
            args.append(path)

        run_command(ffmpeg, *args)

        if not os.path.isfile(path):
            return None  # might be a better idea to raise an exception

        screenshot = ScreenshotFile(path, timecode, self)

        self.screenshots.append(screenshot)

        return screenshot

    def make_screenshots(self, amount, output_dir, ffmpeg=None,
                         frame_accurate=False, extra_args=None):
        screenshots = []

        for number in range(1, amount + 1):
            from os.path import splitext, join

            timecode = int(self.get_duration(ffmpeg).seconds / (amount + 1) *
                           number)

            filename = (splitext(self.filename)[0] +
                        '_screenshot{:02}'.format(number) + '.' +
                        DEFAULT_SCREENSHOT_FILE_EXTENSION)
            output_path = join(output_dir, filename)

            screenshot = self.make_screenshot(output_path, timecode, ffmpeg,
                                              frame_accurate, extra_args)

            screenshots.append(screenshot)

        return screenshots


class ScreenshotFile(AsuFile):
    timecode = Timecode(None, None)
    page_url = None
    thumbnail_url = None

    def __init__(self, path, timecode=None, input_file=None):
        super(ScreenshotFile, self).__init__(path)

        if timecode:
            fmt = "{}:{:02}:{:02}"
            timecode_str = fmt.format(int(timecode / (60 * 60)),
                                      int((timecode / 60) % 60),
                                      int(timecode % 60))
            self.timecode = Timecode(timecode_str, timecode)

        self.input_file = input_file

    def __repr__(self):
        if self.timecode.string:
            return "ScreenshotFile({}, {})".format(self.path,
                                                   self.timecode.string)
        else:
            return "ScreenshotFile({})".format(self.path)


ScreenshotInfo = namedtuple('ScreenshotInfo', 'timecode, page_url, '
                            'thumbnail_url')


class HtmlFile(AsuFile):
    sections = []  # tuples: (filename, [ScreenshotInfo])

    def add_section(self, input_file):
        info_list = []
        for ss in input_file.screenshots:
            info = ScreenshotInfo(ss.timecode.string, ss.page_url,
                                  ss.thumbnail_url)
            info_list.append(info)

        self.sections.append((input_file.filename, info_list))

    @staticmethod
    def _generate_textarea(name, info_list, convert_func):
        links = []
        for info in info_list:
            links.append(convert_func(info.page_url, info.thumbnail_url))

        return ("<td>\n"
                "<b>{}</b><br />\n"
                "<textarea onclick='this.select();' style="
                "'width:300px; height:200px;' />\n"
                "{}\n"
                "</textarea>\n"
                "</td>\n".format(name, ' '.join(links)))

    @staticmethod
    def _generate_input_box(name, link):
        return ("<div>{}</div>\n"
                "<div><input style='width:350px;' type='text' "
                "onClick='this.select();' value='{}' />"
                "</div>\n".format(name, link))

    def write(self):
        file = open(self.path, "w")

        file.write("<?xml version=\"1.0\"?>\n<html>\n<head>\n<style>\n"
                   ".box-shadow {\n"
                   "  -moz-box-shadow: 3px 3px 5px #000000;\n"
                   "  -webkit-box-shadow: 3px 3px 5px #000000;\n"
                   "  box-shadow: 3px 3px 5px #000000;\n"
                   "}\n"
                   "</style>\n</head>\n<body>\n")

        for filename, info_list in self.sections:
            file.write("<font size='5' style='font-weight:bold;'>{}</font>\n"
                       "<hr width='100%'>\n".format(filename))

            file.write("<table style='width:0%;'><td>\n")

            for name, func in (('HTML', markup.to_html),
                               ('BBcode', markup.to_bbcode),
                               ('URLs', markup.to_url)):
                file.write(self._generate_textarea(name, info_list, func))

            file.write("</table>\n")

            for ss_info in info_list:
                link = markup.to_html(ss_info.page_url, ss_info.thumbnail_url)
                file.write("<table class=box-shadow "
                           "style='position:relative;'>\n"
                           "<tr><td rowspan=2>{}</td>".format(link))

                if ss_info.timecode:
                    file.write("<td><font style='font-weight:bold; "
                               "position: absolute; right:0px;\'>{0}</font>"
                               "</td>".format(ss_info.timecode))

                file.write("</tr>\n"
                           "<tr><td>\n")

                for name, func in (('HTML', markup.to_html),
                                   ('BBcode', markup.to_bbcode),
                                   ('URL', markup.to_url)):
                    link = func(ss_info.page_url, ss_info.thumbnail_url)

                    file.write(self._generate_input_box(name, link))

                file.write("</td></tr>\n"
                           "</table>\n")

        file.write("\n</body>\n</html>\n")

        file.close()
