from preditor.gui import qtdesigner


class ConsoleBasePlugin(qtdesigner.QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None):
        super(ConsoleBasePlugin, self).__init__()

        self.initialized = False

    def initialize(self, core):
        if self.initialized:
            return

        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def createWidget(self, parent):
        from preditor.gui.console_base import ConsoleBase

        return ConsoleBase(parent=parent, controller=None)

    def name(self):
        return "ConsoleBase"

    def group(self):
        return "PrEditor Widgets"

    def icon(self):
        from Qt.QtGui import QIcon

        return QIcon("")

    def toolTip(self):
        return ""

    def whatsThis(self):
        return ""

    def isContainer(self):
        return False

    def includeFile(self):
        return "preditor.gui.console_base"

    def domXml(self):
        return '<widget class="ConsoleBase" name="ConsoleBase"/>'
