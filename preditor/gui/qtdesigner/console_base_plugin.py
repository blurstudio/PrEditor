from preditor.gui import qtdesigner


class OutputConsolePlugin(qtdesigner.QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None):
        super(OutputConsolePlugin, self).__init__()

        self.initialized = False

    def initialize(self, core):
        if self.initialized:
            return

        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def createWidget(self, parent):
        from preditor.gui.output_console import OutputConsole

        return OutputConsole(parent=parent, controller=None)

    def name(self):
        return "OutputConsole"

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
        return "preditor.gui.output_console"

    def domXml(self):
        return '<widget class="OutputConsole" name="OutputConsole"/>'
