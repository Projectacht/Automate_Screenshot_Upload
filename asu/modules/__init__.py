import os
import sys
import imp
import inspect
from types import ModuleType


class SpecialImporter(ModuleType):
    def __init__(self, module):
        self.__module__ = module
        self.__name__ = module.__name__

        module_filename = inspect.getfile(inspect.currentframe())
        self._path = os.path.dirname(os.path.abspath(module_filename))

        self._modules = []
        for entry in os.listdir(self._path):
            path = os.path.join(self._path, entry)

            if os.path.isfile(path) and entry.endswith(".py"):
                if entry != "__init__.py":
                    self._modules.append(entry[:-3])
            elif os.path.isdir(path) and "__init__.py" in os.listdir(path):
                self._modules.append(entry)

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

        if not attr.startswith('_') and attr in self._modules:
            self._import(attr)
        else:
            module = imp.load_module(attr, *imp.find_module(attr))
            setattr(self.__module__, attr, module)

        return getattr(self.__module__, attr)

sys.modules[__name__] = SpecialImporter(sys.modules[__name__])
