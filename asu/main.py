from __future__ import print_function

import os
import sys
import webbrowser

from optparse import OptionParser
try:
    from configparser import RawConfigParser, NoSectionError
except ImportError:
    from ConfigParser import RawConfigParser, NoSectionError

from . import (__version__, VALID_INPUT_FILE_EXTENSIONS,
               DEFAULT_SCREENSHOT_AMOUNT)
from . import utils, upload, markup
from .file_type import InputFile, HtmlFile
from .utils import fatal, warn, ffmpeg_exe

SHOW_OPTIONS = ('url', 'html', 'bbcode')


def build_parser():
    usage = 'usage: %prog [options] [<input> ...]'
    version = '%prog {}'.format(__version__)
    parser = OptionParser(usage=usage, version=version)
    parser.add_option('-o', '--output-dir',
                      action='store', type='string', dest='output_dir',
                      help="output dir for generated screenshots and html "
                           "files")
    parser.add_option('-n', '--screenshot-amount',
                      action='store', type='int', dest='screenshot_amount',
                      default=0,
                      help="amount of screenshots to be taken and uploaded, "
                           "default: " + str(DEFAULT_SCREENSHOT_AMOUNT))
    parser.add_option('-N', '--no-upload',
                      action='store_true', dest='no_upload', default=False,
                      help="only generate screenshots and do not upload them")
    parser.add_option('-t', '--thumbnail-size',
                      action='store', type='int', dest='thumbnail_size',
                      default=0,
                      help="size of thumbnail previews, default is dependent "
                           "on image host")
    parser.add_option('-i', '--image-host',
                      action='store', type='string', dest='image_host',
                      help="image host to which the screenshots will be "
                           "uploaded. Default host: " + upload.default_host)
    parser.add_option('--hosts',
                      action='store_true', dest='hosts', default=False,
                      help="show information on host plugins: available "
                           "hosts, max screenshots per input file and "
                           "thumbnail sizes for each host")
    parser.add_option('-l', '--login',
                      action='store', type='string', dest='login',
                      help='username password combo used for logging into '
                           'the image host, seperated by a colon '
                           '(username:password)')
    parser.add_option('-s', '--show',
                      action='store', type='string', dest='show',
                      help="print formated links for uploaded files. "
                           "Possible formats: " + ', '.join(SHOW_OPTIONS))
    parser.add_option('--browser',
                      action='store_true', dest='browser', default=False,
                      help="open generated html page(s), containing links, "
                           "in the browser")
    parser.add_option('--frame-accurate',
                      action='store_true', dest='frame_accurate',
                      default=False,
                      help="ffmpeg's frame accurate search/decode of input "
                           "files, slower, but useful for comparisons")
    parser.add_option('--ffmpeg-arg',
                      action='store', type='string', dest='ffmpeg_arg',
                      help="extra arguments passed to ffmpeg when taking "
                           "screenshots")
    parser.add_option('-c', '--config',
                      action='store', type='string', dest='config',
                      help="location of config file")
    return parser


def parse_options(cfg, options, args):
    if options['hosts']:
        for host_name in upload.hosts:
            host = upload.get_host(host_name)

            fmt = "'{}': max {} screenshots; thumbnail sizes: {}"
            sizes = ", ".join((str(size) for size in host.thumbnail_sizes))
            print(fmt.format(host_name, host.quantity.max, sizes))

        sys.exit(0)

    if options['output_dir'] is not None:
        path = options['output_dir']
        cfg['output_dir'] = os.path.realpath(os.path.normpath(path))
    elif not cfg['output_dir']:
        cfg['output_dir'] = os.path.join(os.getcwd(), "asu_out")

    if not os.path.isdir(cfg['output_dir']):
        os.makedirs(cfg['output_dir'])

    if options['no_upload'] is True:
        if cfg['delete_screenshots'] is True:
            fatal("Commandline argument '--no_upload' cannot be used with "
                  "with the 'delete_screenshots' config option")
        cfg['no_upload'] = True

    if options['login'] is not None:
        if ':' in options['login']:
            cfg['login'] = options['login']
        else:
            fatal("Commandline argument used with '--login' is invalid")

    cfg['image_host'] = (options['image_host'] or cfg['image_host'] or
                         upload.default_host)
    host = upload.get_host(cfg['image_host'])

    if host.quantity.min <= options['screenshot_amount'] <= host.quantity.max:
        cfg['screenshot_amount'] = options['screenshot_amount']
    elif options['screenshot_amount'] != 0:
        fatal("Commandline argument used with '--n-screenshots' is not an "
              "allowed number")

    if options['thumbnail_size'] in host.thumbnail_sizes:
        cfg['thumbnail_size'] = options['thumbnail_size']
    elif options['thumbnail_size'] != 0:
        fatal("Commandline argument used with '--thumbnail-size' was not "
              "an allowed size")
    else:
        cfg['thumbnail_size'] = host.thumbnail_size

    if options['show'] is not None:
        if options['show'] not in SHOW_OPTIONS:
            fatal("Commandline argument used with '--show' is invalid")
        cfg['show'] = options['show']

    if options['browser'] is not False:
        cfg['browser'] = options['browser']

    if options['frame_accurate'] is not False:
        cfg['frame_accurate'] = options['frame_accurate']

    if options['ffmpeg_arg'] is not None:
        cfg['ffmpeg_arg'] = options['ffmpeg_arg']

    return cfg


def main(arguments=None):
    arguments = arguments or sys.argv[1:]

    cfg = {'ffmpeg_command': ffmpeg_exe(),
           'output_dir': None,
           'no_upload': False,
           'image_host': None,
           'browser': False,
           'screenshot_amount': DEFAULT_SCREENSHOT_AMOUNT,
           'thumbnail_size': None,
           'login': None,
           'show': None,
           'frame_accurate': False,
           'ffmpeg_arg': None}

    options, args = build_parser().parse_args()

    if options.config:
        cfgfiles = [options.config]
    else:
        from os.path import sep, expanduser, abspath, dirname

        cfgfiles = [expanduser(sep.join(("~", ".config", "asu", "config"))),
                    expanduser(sep.join(("~", ".asu.cfg"))),
                    sep.join((dirname(dirname(abspath(__file__))), "asu.cfg"))]

    config = RawConfigParser(cfg)
    cfgs_read = config.read(cfgfiles)
    if options.config and options.config not in cfgs_read:
        fatal("Failed to read '" + options.config + "' config file")

    try:
        cfg.update(config.items('asu'))
    except NoSectionError:
        pass

    parse_options(cfg, options.__dict__, args)

    version = utils.ffmpeg_version(cfg['ffmpeg_command'])
    if version is False:
        fatal("Failed to retrieve version number from ffmpeg")
    elif version is None:
        warn("ffmpeg does not look compatible, errors may occur")

    input_files = []
    for arg in args:
        if os.path.isdir(arg):
            # for now just use single level depth
            for f in os.listdir(arg):
                path = os.path.join(arg, f)
                if not os.path.isfile(path):
                    continue

                input_file = InputFile(path)
                if (input_file.exists() and (input_file.ext.lower() in
                                             VALID_INPUT_FILE_EXTENSIONS)):
                    input_files.append(input_file)
            # should an error be returned if no files were added?
        else:
            input_file = InputFile(arg)
            if (input_file.exists() and (input_file.ext.lower() in
                                         VALID_INPUT_FILE_EXTENSIONS)):
                input_files.append(input_file)
            else:
                fatal("Input file argument '{}' is not a valid input "
                      "file".format(arg))

    if len(input_files) == 0:
        fatal("Nothing to do; no input files specified")

    for input_file in input_files:
        input_file.make_screenshots(cfg['screenshot_amount'],
                                    output_dir=cfg['output_dir'],
                                    ffmpeg=cfg['ffmpeg_command'],
                                    frame_accurate=cfg['frame_accurate'],
                                    extra_args=cfg['ffmpeg_arg'])

    if cfg['no_upload']:
        for input_file in input_files:
            for ss in input_file.screenshots:
                print(ss.path)
            print()

        sys.exit(0)

    if cfg['login']:
        username, _, password = cfg['login'].partition(':')
    else:
        username, password = None, None

    Host = upload.get_host(cfg['image_host'])
    image_host = Host(username=username, password=password,
                      thumbnail_size=cfg['thumbnail_size'])

    html_file = HtmlFile(os.path.join(cfg['output_dir'], "out.html"))

    for input_file in input_files:
        uploads = image_host.upload([ss.path for ss in input_file.screenshots])

        for ss, (_, page, thumb) in zip(input_file.screenshots, uploads):
            ss.page_url = page
            ss.thumbnail_url = thumb

        html_file.add_section(input_file)

    html_file.write()

    if cfg['browser']:
        webbrowser.open_new_tab(html_file.path)

    if cfg['show']:
        markup_func = {'url': markup.to_url,
                       'html': markup.to_html,
                       'bbcode': markup.to_bbcode}[cfg['show']]

        for input_file in input_files:
            for ss in input_file.screenshots:
                print(markup_func(ss.page_url, ss.thumbnail_url))
            print()
    else:
        print(html_file.path)
