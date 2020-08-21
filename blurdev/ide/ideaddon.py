##
# 	\namespace	blurdev.ide.ideaddon
#
# 	\remarks	Creates the base class for Addons that allow developers to extend
#               the IDE through plugins
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/06/11
#

import sys
import os.path
import traceback

from blurdev import debug

from blurdev.decorators import abstractmethod


class IdeAddonModule(object):
    def __init__(self, name, path=''):
        self._name = name
        self._path = path
        self._status = 'created'
        self._errors = ''
        self._enabled = True

    def addons(self):
        return [
            addon
            for addon in IdeAddon.addons.values()
            if self._name in addon.__module__
        ]

    def errors(self):
        return self._errors

    def name(self):
        return self._name

    def isEnabled(self):
        return self._enabled

    def init(self, ide):
        # register the module path for import
        if self._path and not os.path.normcase(self._path) in sys.path:
            sys.path.append(os.path.normcase(self._path))

        # import the module
        try:
            __import__(self._name)
            sys.modules[self._name].init()
            self._status = 'loaded'
        except Exception:
            self._errors = traceback.format_exc()
            self._status = 'errored'

        # go through and activate them
        for addon in IdeAddon.addons.values():
            if self._name in addon.__module__:
                if addon.isEnabled():
                    if debug.isDebugLevel(debug.DebugLevel.High):
                        addon.activate(ide)
                        status = 'active'
                        errors = []
                    else:
                        try:
                            addon.activate(ide)
                            status = 'active'
                            errors = []
                        except Exception:
                            errors = [
                                'Addon: ',
                                addon.name(),
                                'errored during activation.',
                                traceback.format_exc(),
                            ]
                            status = 'errored'

                    addon.setStatus(status)
                    addon.setErrors('\n'.join(errors))

    def path(self):
        return self._path

    def setName(self, name):
        self._name = name

    def setPath(self, path):
        self._path = path

    def setEnabled(self, state=True, ide=None):
        if state == self._enabled:
            return True

        # use the core ide by default
        if not ide:
            import blurdev

            ide = blurdev.core.ideeditor()

        for addon in self.addons():
            addon.setEnabled(state, ide)

    def setStatus(self, status):
        self._status = status

    def status(self):
        return self._status


class IdeAddon(object):
    addons = {}
    modules = {
        # load the built-in addons
        'blurdev.ide.addons': IdeAddonModule('blurdev.ide.addons'),
    }

    def __init__(self, name):
        self._enabled = True
        self._name = name
        self._status = 'loaded'
        self._errors = ''

    @abstractmethod
    def activate(self, ide):
        return False

    @abstractmethod
    def deactivate(self, ide):
        return False

    def disable(self):
        return self.setEnabled(False)

    def enable(self):
        return self.setEnabled(True)

    def errors(self):
        return self._errors

    def name(self):
        return self._name

    def isEnabled(self):
        return self._enabled

    def setEnabled(self, state=True, ide=None):
        if state == self._enabled:
            return True

        # use the core ide by default
        if not ide:
            import blurdev

            ide = blurdev.core.ideeditor()

        result = True
        errors = ''
        status = 'loaded'

        # update for the ide
        if ide:
            if state:
                try:
                    result - self.activate(ide)
                    status = 'active'
                except Exception:
                    errors = [
                        'Addon: ',
                        self.name(),
                        'errored during activation.',
                        traceback.format_exc(),
                    ]
                    status = 'errored'
            else:
                try:
                    result = self.deactivate(ide)
                    status = 'inactive'
                except Exception:
                    errors = [
                        'Addon: ',
                        self.name(),
                        'errored during deactivation.',
                        traceback.format_exc(),
                    ]
                    self._status = 'errored'
                    result = False

            self._status = status
            self._errors = '\n'.join(errors)

        return result

    def setErrors(self, errors):
        self._errors = errors

    def setStatus(self, status):
        self._status = status

    def status(self):
        return self._status

    @staticmethod
    def find(name):
        return IdeAddon.addons.get(name)

    @staticmethod
    def register(name, cls):
        IdeAddon.addons[name] = cls(name)

    @staticmethod
    def registerErrored(package, error):
        IdeAddon.addons[package] = IdeAddonError(package, error)

    @staticmethod
    def init(ide):
        # load additional addons from the environment
        for key in os.environ.keys():
            if key.startswith('BDEV_IDE_ADDON_'):
                valsplit = os.environ[key].split(',')
                if len(valsplit) == 2:
                    module = valsplit[0]
                    path = valsplit[1]
                else:
                    module = valsplit[0]
                    path = ''

                IdeAddon.modules[module] = IdeAddonModule(module, path)

        # load the various addon modules
        for module in IdeAddon.modules.values():
            module.init(ide)


class IdeAddonError(IdeAddon):
    def __init__(self, package, error):
        super(IdeAddonError, self).__init__(self)
        self._name = package
        self.__module__ = package
        self._errors = error
        self._status = 'errored'

    def activate(self, ide):
        return False

    def deactivate(self, ide):
        return False

    def setEnabled(self, state=True, ide=None):
        return False
