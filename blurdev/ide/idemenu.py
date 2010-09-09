##
# 	\namespace	blurdev.ide.plugin
#
# 	\remarks	The Plugin class defines the common base class that all plugins will inherit from
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtGui import QMenu


class IdeMenu(QMenu):
    def __init__(self, parent, tool=None):
        QMenu.__init__(self, parent)

        self.setTitle('Developers...')

        self._tool = tool

        # create the actions
        import blurdev

        if tool and not tool.isNull():
            self.addAction('Edit Tool...').triggered.connect(self.editPackage)

        self.addAction('Template Builder...').triggered.connect(self.buildTemplate)
        self.addSeparator()
        self.addAction('Logger..').triggered.connect(blurdev.core.showLogger)

    def buildTemplate(self):
        from blurdev.ide.templatebuilder import TemplateBuilder

        TemplateBuilder.createTemplate()

    def editPackage(self):

        from PyQt4.QtCore import QDir

        QDir.setCurrent(self._tool.path())
