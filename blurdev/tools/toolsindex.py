from __future__ import absolute_import

import glob
import os
import re

from PyQt4.QtCore import QObject

import blurdev
import blurdev.tools.toolscategory
import blurdev.tools.tool
import blurdev.tools.toolsfavoritegroup


class ToolsIndex(QObject):
    """ Defines the indexing system for the tools package
    """

    def __init__(self, environment):
        QObject.__init__(self, environment)
        self._loaded = False
        self._favoritesLoaded = False
        self._categoryCache = {}
        self._toolCache = {}

    def baseCategories(self):
        """ returns the categories that are parented to this index
        """
        self.load()
        output = [cat for cat in self._categoryCache.values() if cat.parent() == self]
        output.sort(lambda x, y: cmp(x.objectName(), y.objectName()))
        return output

    def clear(self):
        """ clears the current cache of information
        """
        # save the favorites first
        self.saveFavorites()
        # reload the data
        self._favoritesLoaded = False
        self._loaded = False
        self._categoryCache.clear()
        self._toolCache.clear()

        # remove all the children
        for child in self.findChildren(
            blurdev.tools.toolsfavoritegroup.ToolsFavoriteGroup
        ):
            child.setParent(None)
            child.deleteLater()

        for child in self.findChildren(blurdev.tools.tool.Tool):
            child.setParent(None)
            child.deleteLater()

        for child in self.findChildren(blurdev.tools.toolscategory.ToolsCategory):
            child.setParent(None)
            child.deleteLater()

    def categories(self):
        """ returns the current categories for this index
        """
        self.load()
        output = self._categoryCache.values()
        output.sort(lambda x, y: cmp(x.objectName(), y.objectName()))
        return output

    def cacheCategory(self, category):
        """ caches the category
        """
        self._categoryCache[str(category.objectName())] = category

    def cacheTool(self, tool):
        """ caches the inputed tool by its name
        """
        self._toolCache[str(tool.objectName())] = tool

    def environment(self):
        """ returns this index's environment
        """
        return self.parent()

    def rebuild(self):
        """ rebuilds the index from the file system
        """
        doc = blurdev.XML.XMLDocument()
        root = doc.addNode('index')

        # walk through the hierarchy
        categories = root.addNode('categories')
        tools = root.addNode('tools')
        legacy = root.addNode('legacy')

        # go through all the different language tool folders
        # MCH 07/11/12: This is necessary for backwards compatibility until we switch over to the flat hierarchy
        if os.path.isdir(
            self.environment().relativePath('code/python/tools/External_Tools')
        ):
            # This is for the old tools system and is very blur specific
            relPath = 'code/*/tools/*/'
        else:
            # This is for the new tools system
            relPath = 'code/*/tools/'
        for path in glob.glob(self.environment().relativePath(relPath)):
            self.rebuildPath(path, categories, tools)

        # go through the legacy folders
        for path in glob.glob(
            self.environment().relativePath('maxscript/treegrunt/main/*/')
        ):
            self.rebuildPath(path, categories, tools, True)

        # save the index file
        doc.save(self.filename())

        # clear the old data & reload
        self.clear()
        self.load()
        self.loadFavorites()

    def rebuildPath(self, path, parent, tools, legacy=False, parentCategoryId=''):
        """ rebuilds the tool information recursively for the inputed path and tools
            
            :param path: str
            :param parent: <blurdev.XML.XMLElement>
            :param tools: <blurdev.XML.XMLElement>
            :param legacy: bool
            :param parentCategoryId: str
        """

        def setValueForNode(cat, category='category', name='name', value=''):
            """ Returns the requested node if it exists, or creates and sets it if it does not. """
            if cat.attribute(name) == value:
                return cat
            for child in cat.children():
                if child.attribute(name) == value:
                    return child
            child = cat.addNode(category)
            child.setAttribute(name, value)
            return child

        def copyXmlData(toolPath, node, categoryId):
            """ Copys the contents of the metadata xml file into the tools index. """
            # store the tool information
            doc = blurdev.XML.XMLDocument()
            if doc.load(toolPath) and doc.root():
                node.addChild(doc.root())
                child = doc.root().findChild('category')
                if child:
                    categoryId = '::'.join(
                        [split.strip('_') for split in child.value().split('::')]
                    )
                    # build the category data
                    splits = categoryId.split("::")
                    cat = parent
                    while splits:
                        cat = setValueForNode(cat, 'category', 'name', splits[0])
                        count = len(splits)
                        if count > 2:
                            splits = [
                                '::'.join((splits[0], splits[1].strip('_')))
                            ] + splits[2:]
                        elif count > 1:
                            splits = ['::'.join((splits[0], splits[1].strip('_')))]
                        else:
                            splits = []
                node.setAttribute('category', categoryId)
            else:
                print 'Error loading tool: ', toolPath

        def processLegacyXmlFiles(script, node, categoryId, xmls):
            """ If a matching xml file exists add its contents to the index """
            # Note: If there is a python and maxscript tool with the same name, this xml will be applied to both of them.
            toolPath = '{}.xml'.format(os.path.splitext(script)[0])
            if toolPath in xmls:
                copyXmlData(toolPath, toolIndex, categoryId)

        foldername = os.path.normpath(path).split(os.path.sep)[-1].strip('_')
        if parentCategoryId:
            categoryId = parentCategoryId + '::' + foldername
        else:
            categoryId = foldername

        categoryId = '::'.join([split.strip('_') for split in categoryId.split('::')])

        # create a category
        categoryIndex = parent.findChildById(categoryId)
        if not categoryIndex:
            categoryIndex = parent.addNode('category')
            categoryIndex.setAttribute('name', categoryId)

        # add non-legacy tools
        processed = []
        if not legacy:
            paths = glob.glob(path + '/*/__meta__.xml')

            for toolPath in paths:
                toolId = os.path.normpath(toolPath).split(os.path.sep)[-2]
                toolIndex = tools.addNode('tool')
                toolIndex.setAttribute('name', toolId)
                toolIndex.setAttribute('category', categoryId)
                toolIndex.setAttribute(
                    'loc', self.environment().stripRelativePath(toolPath)
                )

                copyXmlData(toolPath, toolIndex, categoryId)

                processed.append(toolPath)

        # add legacy tools
        else:
            # add maxscript legacy tools
            scripts = glob.glob(path + '/*.ms')
            xmls = set(glob.glob(os.path.join(path, '*.xml')))
            for script in scripts:
                toolId = os.path.splitext(os.path.basename(script))[0]
                toolIndex = tools.addNode('legacy_tool')
                toolIndex.setAttribute('category', categoryId)
                toolIndex.setAttribute('name', 'LegacyStudiomax::%s' % toolId)
                toolIndex.setAttribute('src', script)
                toolIndex.setAttribute('type', 'LegacyStudiomax')
                toolIndex.setAttribute('icon', 'icon24.bmp')
                processLegacyXmlFiles(script, toolIndex, categoryId, xmls)

            # add python legacy tools
            scripts = glob.glob(path + '/*.py*')
            for script in scripts:
                if not os.path.splitext(script)[1] == '.pyc':
                    if 'External_Tools' in script:
                        typ = 'LegacyExternal'
                    else:
                        typ = 'LegacySoftimage'

                    toolId = os.path.splitext(os.path.basename(script))[0]
                    toolIndex = tools.addNode('legacy_tool')
                    toolIndex.setAttribute('category', categoryId)
                    toolIndex.setAttribute('name', '%s::%s' % (typ, toolId))
                    toolIndex.setAttribute('src', script)
                    toolIndex.setAttribute('type', typ)

                    if typ == 'LegacyExternal':
                        toolIndex.setAttribute('icon', 'img/icon.png')
                    else:
                        toolIndex.setAttribute('icon', 'icon24.bmp')
                    processLegacyXmlFiles(script, toolIndex, categoryId, xmls)

            # add link support
            links = glob.glob(path + '/*.lnk')
            for link in links:
                toolId = os.path.splitext(os.path.basename(link))[0]
                toolIndex = tools.addNode('legacy_tool')
                toolIndex.setAttribute('category', categoryId)
                toolIndex.setAttribute('name', 'LegacyExternal::%s' % toolId)
                toolIndex.setAttribute('src', link)
                toolIndex.setAttribute('type', 'LegacyExternal')

        # add subcategories
        subpaths = glob.glob(path + '/*/')
        for path in subpaths:
            if not (
                os.path.split(path)[0].endswith('_resource')
                or (path + '__meta__.xml' in processed)
            ):
                self.rebuildPath(path, categoryIndex, tools, legacy, categoryId)

    def reload(self):
        """Reload the index without rebuilding it. This will allow users to refresh the index without restarting treegrunt."""
        self.clear()
        self.load()
        self.loadFavorites()

    def favoriteGroups(self):
        """ returns the favorites items for this index
        """
        self.loadFavorites()
        return [
            child
            for child in self.findChildren(
                blurdev.tools.toolsfavoritegroup.ToolsFavoriteGroup
            )
            if child.parent() == self
        ]

    def favoriteTools(self):
        """ returns all the tools that are favorited and linked
        """
        self.loadFavorites()
        return [
            tool
            for tool in self._toolCache.values()
            if tool.isFavorite() and tool.favoriteGroup() == None
        ]

    def filename(self):
        """ returns the filename for this index
        """
        return self.environment().relativePath('code/tools.xml')

    def load(self):
        """ loads the current index from the system
        """
        if not self._loaded:
            self._loaded = True
            doc = blurdev.XML.XMLDocument()

            filename = self.filename()
            if doc.load(filename):
                root = doc.root()

                # load categories
                categories = root.findChild('categories')
                if categories:
                    for xml in categories.children():
                        blurdev.tools.toolscategory.ToolsCategory.fromIndex(
                            self, self, xml
                        )

                # load tools
                tools = root.findChild('tools')
                if tools:
                    for xml in tools.children():
                        blurdev.tools.tool.Tool.fromIndex(self, xml)

    def loadFavorites(self):
        if not self._favoritesLoaded:
            self._favoritesLoaded = True
            # load favorites
            pref = blurdev.prefs.find(
                'treegrunt/%s_favorites' % (self.environment().objectName())
            )
            children = pref.root().children()
            for child in children:
                if child.nodeName == 'group':
                    blurdev.tools.toolsfavoritegroup.ToolsFavoriteGroup.fromXml(
                        self, self, child
                    )
                else:
                    self.findTool(child.attribute('id')).setFavorite(True)

    def findCategory(self, name):
        """ returns the tool based on the inputed name, returning the default option if no tool is found
        """
        self.load()
        return self._categoryCache.get(str(name))

    def findTool(self, name):
        """ returns the tool based on the inputed name, returning the default option if no tool is found
        """
        self.load()
        return self._toolCache.get(str(name), blurdev.tools.tool.Tool())

    def findToolsByCategory(self, name):
        """ looks up the tools based on the inputed category name
        """
        self.load()
        output = [
            tool for tool in self._toolCache.values() if tool.categoryName() == name
        ]
        output.sort(
            lambda x, y: cmp(str(x.objectName().lower()), str(y.objectName().lower()))
        )
        return output

    def findToolsByLetter(self, letter):
        """ looks up tools based on the inputed letter
        """
        self.load()

        if letter == '#':
            regex = re.compile('\d')
        else:
            regex = re.compile('[%s%s]' % (str(letter.upper()), str(letter.lower())))

        output = []
        for key, item in self._toolCache.items():
            if regex.match(key):
                output.append(item)

        output.sort(lambda x, y: cmp(x.name().lower(), y.name().lower()))

        return output

    def saveFavorites(self):
        # load favorites
        if self._favoritesLoaded:
            pref = blurdev.prefs.find(
                'treegrunt/%s_favorites' % (self.environment().objectName())
            )
            root = pref.root()
            root.clear()

            # record the groups
            for grp in self.favoriteGroups():
                grp.toXml(root)

            # record the tools
            for tool in self.favoriteTools():
                node = root.addNode('tool')
                node.setAttribute('id', tool.objectName())
            pref.save()

    def search(self, searchString):
        """ looks up tools by the inputed search string
        """
        self.load()
        expr = re.compile(str(searchString).replace('*', '.*'), re.IGNORECASE)
        output = []
        for tool in self._toolCache.values():
            if expr.search(tool.displayName()):
                output.append(tool)

        output.sort(
            lambda x, y: cmp(str(x.objectName()).lower(), str(y.objectName()).lower())
        )
        return output

    def tools(self):
        return self._toolCache.values()

    def toolNames(self):
        return self._toolCache.keys()
