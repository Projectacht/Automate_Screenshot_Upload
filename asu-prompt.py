#!/usr/bin/env python

import sys
import os
from os import path

from asu import VALID_INPUT_FILE_EXTENSIONS
from asu.utils import run_command

if sys.version_info[0] < 3:
    input = raw_input

asu_exe = path.sep.join((path.dirname(path.abspath(__file__)), "asu.py"))


def get_path_exists(string=None, file_type=None):
    if string is None:
        string = input()
    while True:
        if string == '':
            print('Cannot be left empty, please try again')
        else:
            tmp = path.realpath(path.normpath(string.strip(' \'\"')))
            if file_type == 'dir':
                if path.isdir(tmp):
                    return tmp
                print('Path to directory does not exist, please try again')
            elif file_type == 'file':
                if path.isfile(tmp):
                    return tmp
                print('Path to file does not exist, please try again')
            else:
                if path.exists(tmp):
                    return tmp
                print('Path does not exist, please try again')
        string = input()


print('Input video file or dir containing video files:')
input_files = []
filename = get_path_exists()
if path.isfile(filename):
    ext = path.splitext(filename)[1].lower()
    if ext[1:] in VALID_INPUT_FILE_EXTENSIONS:
        input_files.append(filename)
    else:
        sys.exit('ERROR: \'' + filename + '\' is not a eligible file.')
elif path.isdir(filename):
    success = False
    for f in os.listdir(filename):
        ext = path.splitext(f)[1].lower()
        if ext[1:] in VALID_INPUT_FILE_EXTENSIONS:
            input_files.append(path.join(filename, f))
            success = True
    if success is False:
        sys.exit('ERROR: No eligible files found in ' + filename + '.')
else:
    sys.exit('ERROR: \'' + filename + '\' is not a file or a directory.')

ret, _, _ = run_command('python', *[asu_exe] + sys.argv[1:] + input_files,
                        stdout=None, stderr=None)

sys.exit(ret)
