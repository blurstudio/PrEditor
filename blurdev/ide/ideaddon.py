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

from blurdev.decorators import abstractmethod


class IdeAddon(object):
    addons = {}

    def __init__(self, name):
        self._enabled = True
        self._name = name

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

        # set the enabled state
        self._enabled = state

        # update for the ide
        if ide:
            if state:
                try:
                    return self.activate(ide)
                except:
                    print 'Addon: ', self.name(), 'errored during activation.'
                    return False
            else:
                try:
                    return self.deactivate(ide)
                except:
                    print 'Addon: ', self.name(), 'errored during deactivation.'
                    return False
        else:
            return True

    @staticmethod
    def find(name):
        return IdeAddon.addons.get(name)

    @staticmethod
    def register(name, cls):
        IdeAddon.addons[name] = cls(name)

    @staticmethod
    def init(ide):
        # load the addon plugins
        from blurdev.ide import addons

        addons.init()

        # go through and activate them
        for addon in IdeAddon.addons.values():
            if addon.isEnabled():
                try:
                    addon.activate(ide)
                except:
                    print 'Addon: ', addon.name(), 'errored during activation.'
