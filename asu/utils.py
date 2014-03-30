from __future__ import print_function

import os
import sys
import re
import subprocess

from . import DEFAULT_FFMPEG_COMMAND


def warn(*args, **kwargs):
    print("Warn:", *args, file=sys.stderr, **kwargs)


def fatal(*args, **kwargs):
    print("Error:", *args, file=sys.stderr, **kwargs)

    sys.exit(1)


def quote_path(string):
    if 'win32' in sys.platform:
        return '"' + string + '"'
    else:
        return '\'' + string + '\''


def regex_in_string(regex, string):
    match = None

    if isinstance(regex, str):
        match = re.search(regex, string)
    else:  # compiled regex
        match = regex.search(string)

    if match:
        return match.group()


def run_command(executeable, *args, **kwargs):
    stdout = kwargs.pop('stdout', subprocess.PIPE)
    stderr = kwargs.pop('stderr', subprocess.PIPE)

    command_input = (executeable,)
    if len(args) > 0:
        if 'win32' in sys.platform:
            command_input = (executeable, tuple(' ' + obj for obj in args))
        else:
            command_input += args

    proc = subprocess.Popen(command_input, stdout=stdout, stderr=stderr)
    stdout, stderr = proc.communicate()

    return proc.returncode, stdout, stderr


def ffmpeg_version(ffmpeg):
    re_version = re.compile(r'^(ffmpeg|avconv) version.*$')
    retcode, stdout, _ = run_command(ffmpeg, '-version')

    if retcode != 0:
        return False
    return regex_in_string(re_version, stdout.decode().split('\n')[0])


def ffmpeg_exe(path=None, default=None):
    if 'win32' in sys.platform:
        from os.path import abspath, dirname, join, isfile

        ffmpeg = join(dirname(abspath(path or __file__)), 'ffmpeg', 'bin',
                      'ffmpeg.exe')
        if isfile(ffmpeg):
            return ffmpeg

    return default or DEFAULT_FFMPEG_COMMAND
