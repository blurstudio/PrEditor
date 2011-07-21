##
# 	\namespace	blurdev.gui.dialogs.configdialog.configset
#
# 	\remarks	Defines the ConfigSet class that will manage config widgets
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/20/10
#

import copy
import glob
import os.path
import sys

from PyQt4.QtCore import QObject, pyqtSignal


class ConfigSection(object):
    def __init__(
        self, configSet, name, widgetClass, properties={}, group='Default', icon=''
    ):
        self._configSet = configSet
        self._name = name
        self._properties = dict(properties)
        self._widgetClass = widgetClass
        self._group = group
        self._icon = icon

    def copyFrom(self, other):
        self._properties = copy.deepcopy(other._properties)

    def configSet(self):
        return self._configSet

    def group(self):
        return self._group

    def icon(self):
        return self._icon

    def name(self):
        return self._name

    def properties(self):
        return self._properties.keys()

    def recordToXml(self, xml):
        xsection = xml.addNode('section')
        xsection.setAttribute('name', self.uniqueName())
        for key, value in self._properties.items():
            xsection.recordProperty(key, value)

    def restoreFromXml(self, xml):
        for key in self._properties.keys():
            value = xml.restoreProperty(key)
            if value != None:
                self._properties[key] = value

    def setValue(self, key, value):
        self._properties[str(key)] = value

    def uniqueName(self):
        return '%s::%s' % (self.group(), self.name())

    def value(self, key, default=None):
        return self._properties.get(str(key), default)

    def widget(self, parent):
        # make sure we have a widget class
        if not self._widgetClass:
            return None

        # create the new widget instance
        return self._widgetClass(self, parent)


# ---------------------------------------------------------------


class ConfigSet(QObject):
    settingsChanged = pyqtSignal()

    def __init__(self, prefname=''):
        super(ConfigSet, self).__init__()
        self._prefname = prefname
        self._sections = {}
        self._customData = {}

    def copyFrom(self, other):
        for section in other.sections():
            msection = self.section(section.uniqueName())
            if msection:
                msection.copyFrom(section)

    def customData(self, key, default=None):
        return self._customData.get(key, default)

    def edit(self, parent=None, defaultSection=''):
        from blurdev.gui.dialogs.configdialog import ConfigDialog

        return ConfigDialog.edit(self, parent, defaultSection)

    def emitSettingsChanged(self):
        if not self.signalsBlocked():
            self.settingsChanged.emit()

    def loadPlugins(self, module):
        filenames = glob.glob(os.path.dirname(module.__file__) + '/*.py')
        for filename in filenames:
            modname = os.path.basename(filename).split('.')[0]
            if modname != '__init__':
                configmodname = '%s.%s' % (module.__name__, modname)
                try:
                    __import__(configmodname)
                except:
                    print 'could not import %s' % configmodname
                    continue

                configmod = sys.modules.get(configmodname)
                if configmod:
                    configmod.registerSections(self)

    def registerSection(
        self, name, widgetClass, properties={}, group='Default', icon=''
    ):
        section = ConfigSection(self, name, widgetClass, properties, group, icon)
        if not group:
            group = 'Default'
        self._sections['%s::%s' % (group, name)] = section
        return section

    def recordToXml(self, xml):
        xconfig = xml.findChild('config')
        if xconfig:
            xconfig.clear()
        else:
            xconfig = xml.addNode('config')

        for section in self.sections():
            section.recordToXml(xconfig)

    def save(self):
        if not self._prefname:
            return False
        from blurdev import prefs

        pref = prefs.find(self._prefname)

        self.recordToXml(pref.root())

        pref.save()

        self.emitSettingsChanged()
        return True

    def restoreFromXml(self, xml):
        xconfig = xml.findChild('config')
        if not xconfig:
            return False

        for xsection in xconfig.children():
            section = self.section(xsection.attribute('name'))
            if section:
                section.restoreFromXml(xsection)

        self.emitSettingsChanged()
        return True

    def restore(self):
        if not self._prefname:
            return False
        from blurdev import prefs

        pref = prefs.find(self._prefname)

        return self.restoreFromXml(pref.root())

    def section(self, name):
        return self._sections.get(str(name))

    def sections(self):
        return self._sections.values()

    def sectionGroups(self):
        output = list(set([section.group() for section in self.sections()]))
        output.sort()
        return output

    def sectionsInGroup(self, group):
        output = [section for section in self.sections() if (section.group() == group)]
        output.sort(lambda x, y: cmp(x.name(), y.name()))
        return output

    def setCustomData(self, key, value):
        self._customData[str(key)] = value
