import os
import sys
import imp
import inspect
from types import ModuleType
from collections import namedtuple

UploadRange = namedtuple('UploadRange', 'min, max')

UploadedFile = namedtuple('UploadedFile', 'filename, page_url, thumbnail_url')


class BaseHost(object):
    """Base class from which all image host plugins need to inherit.

    The following attributes need to be valid for all the subclasses"""
    # min/max amount of images to be uploaded at once
    quantity = UploadRange(-1, -1)

    thumbnail_sizes = ()  # tuple containing all possible thumbnail sizes
    thumbnail_size = -1  # value from above tuple

    username = None  # used for login
    password = None  # ditto

    uploaded_files = []  # list containing UploadedFile tuples

    def __init__(self, username=None, password=None, thumbnail_size=None):
        raise NotImplementedError

    def upload(self, files):
        raise NotImplementedError


class SpecialImporter(ModuleType):
    default_host = 'imagebam'  # set prefered host, module needs to exist

    def __init__(self, module):
        self.__module__ = module
        self.__name__ = module.__name__

        module_filename = inspect.getfile(inspect.currentframe())
        self._path = os.path.dirname(os.path.abspath(module_filename))

        self.hosts = []
        for entry in os.listdir(self._path):
            path = os.path.join(self._path, entry)

            if os.path.isfile(path) and entry.endswith(".py"):
                if entry != "__init__.py":
                    self.hosts.append(entry[:-3])
            elif os.path.isdir(path) and "__init__.py" in os.listdir(path):
                self.hosts.append(entry)

    def _import(self, name):
        info = imp.find_module(name, [self._path])
        try:
            module = imp.load_module(name, *info)
        finally:
            if info[0]:
                info[0].close()

        setattr(self.__module__, name, module)

    def __getattr__(self, attr):
        if getattr(self.__module__, attr, None):
            return getattr(self.__module__, attr)

        if not attr.startswith('_') and attr in self.hosts:
            self._import(attr)

        return getattr(self.__module__, attr)

    def get_host(self, host_name):
        return getattr(self, host_name).Host

sys.modules[__name__] = SpecialImporter(sys.modules[__name__])
