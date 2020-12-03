from Qt.QtCore import QObject

import blurdev.tools.toolsindex
import blurdev.tools.tool


class ToolsCategory(QObject):
    """ Creates the ToolsCategory class for grouping tools together
    """

    def __init__(self, parent, name=None):
        QObject.__init__(self, parent)
        self._toolTypeLoaded = False
        self._toolType = 0
        if name is not None:
            self.setObjectName(name)

    def addTool(self, tool):
        """ adds the tool to the cache
        """
        tool.setParent(self)
        self._toolType |= tool.toolType()

    def displayName(self):
        name = str(self.objectName()).split('::')[-1]
        return name.replace('_', ' ').strip()

    def index(self):
        """ returns the index from which this category is instantiated
        """
        output = self.parent()
        while output and not isinstance(output, blurdev.tools.toolsindex.ToolsIndex):
            output = output.parent()
        return output

    def subcategories(self):
        """ returns a list of the sub-categories for this category
        """
        return [child for child in self.children() if isinstance(child, ToolsCategory)]

    def tools(self, toolType=None):
        """ returns a list of the tools for this category
        """
        return [
            child
            for child in self.children()
            if isinstance(child, blurdev.tools.tool.Tool)
        ]

    def toolType(self):
        """ returns the toolType for this category
        """
        if not self._toolTypeLoaded:
            self._toolTypeLoaded = True
            for cat in self.subcategories():
                self._toolType |= cat.toolType()
        return self._toolType

    @classmethod
    def fromIndex(cls, index, parent, name=None, children={}):
        output = cls(parent, name)

        # cache the category
        index.cacheCategory(output)

        # load the child categories
        for childName in children:
            cls.fromIndex(index, output, childName, children=children[childName])
        return output
