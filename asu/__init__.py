from collections import namedtuple

components = 'major, minor, micro, releaselevel, serial'
values = (0, 10, 0, 'beta', 0)
__version_info__ = namedtuple('__version_info__', components)(*values)
__version__ = (str(__version_info__.major) + '.' +
               str(__version_info__.minor) + ' ' +
               __version_info__.releaselevel)
del components, values

VALID_INPUT_FILE_EXTENSIONS = ('mkv', 'avi', 'm2ts', 'ts', 'mp4', 'vob')

DEFAULT_SCREENSHOT_AMOUNT = 3

DEFAULT_OUTPUT_FILE_TYPE = 'png'
DEFAULT_SCREENSHOT_FILE_EXTENSION = 'png'

DEFAULT_FFMPEG_COMMAND = 'ffmpeg'
