from __future__ import absolute_import

import os
import re
import glob
import logging
import shutil
import tempfile

try:
    # simplejson parses json faster than python 2.7's json module.
    # Use it if its installed.
    import simplejson as json
except ImportError:
    import json

from Qt.QtCore import QObject

import blurdev
import blurdev.tools.toolscategory
import blurdev.tools.tool
import blurdev.tools.toolsfavoritegroup
from collections import OrderedDict


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

    def rebuild(self, filename=None, configFilename=True):
        """ rebuilds the index from the file system.
        
        This does not create any necessary directory structure to save the files.
        
        Args:
            filename (str): If filename is not provided it will store the file in self.filename(). 
                This is the location that treegrunt looks for its tools.xml file.
            configFilename (str|bool): if True, save as config.ini next to filename. If a file path
                is provided save to that file path. 
        """
        # If a filename was not provided get the default
        if not filename:
            filename = self.filename()
        # Build the new file so updated blurdev's can use it.
        self._rebuildJson(filename=filename)
        if configFilename and blurdev.settings.OS_TYPE == 'Windows':
            # We only use config.ini on windows systems for maxscript
            if isinstance(configFilename, bool):
                configFilename = os.path.join(os.path.dirname(filename), 'config.ini')
            envPath = self.parent().path()
            with blurdev.ini.temporaryDefaults():
                blurdev.ini.SetINISetting(
                    configFilename, 'GLOBALS', 'environment', 'DEFAULT'
                )
                blurdev.ini.SetINISetting(configFilename, 'GLOBALS', 'version', 2.0)
                blurdev.ini.SetINISetting(
                    configFilename,
                    'DEFAULT',
                    'coderoot',
                    os.path.join(envPath, 'maxscript', 'treegrunt'),
                )
                blurdev.ini.SetINISetting(
                    configFilename,
                    'DEFAULT',
                    'startuppath',
                    os.path.join(envPath, 'maxscript', 'treegrunt', 'lib'),
                )

        # clear the old data & reload
        self.clear()
        self.load()
        self.loadFavorites()

    def _rebuildJson(self, filename):
        categories = {}
        tools = []

        # Add tools in each of the programming language tools folders.
        path = self.environment().relativePath('code/python/tools/')
        self.rebuildPathJson(path, categories, tools)

        # Add tools in the legacy folder.
        try:
            import legacy

            path = os.path.dirname(legacy.__file__)
            for path in glob.glob(os.path.join(os.path.join(path, 'tools', '*'))):
                self.rebuildPathJson(path, categories, tools, legacy=True)
        except ImportError as error:
            logging.error(error)

        # Use OrderedDict to build this so the json is saved consistently.
        dirname, basename = os.path.split(filename)
        output = OrderedDict(categories=categories)
        output['tools'] = tools
        name, extension = os.path.splitext(basename)

        # Generating JSON index in a temporary location.
        # Once succesfully generated we will copy the file where it needs to go.
        with tempfile.NamedTemporaryFile(prefix=name, suffix=extension) as fle:
            json.dump(output, fle, indent=4)
            fle.seek(0)
            with open(filename, 'w') as out:
                shutil.copyfileobj(fle, out)

            # Copying the tool index to the orignal location for backwards compatibility.
            # Essentially host that will have the old blurdev will still look in the old place.
            # TODO: Remove this block once everyone has versions 2.11.0.
            if os.path.exists(os.path.join(dirname, 'code')):
                # The read head is at the end of the file, move it back to the start of the
                # file so we can copy it again.
                fle.seek(0)
                with open(os.path.join(dirname, 'code', basename), 'w') as out:
                    shutil.copyfileobj(fle, out)

    def rebuildPathJson(
        self, path, categories, tools, legacy=False, parentCategoryId=None
    ):

        foldername = os.path.normpath(path).split(os.path.sep)[-1].strip('_')
        if parentCategoryId:
            categoryId = parentCategoryId + '::' + foldername
        else:
            categoryId = foldername

        def addToolCategory(category):
            """ Update the categories dict to include this category

            if passed 'External_Tools::Production_Tools::Proxy Tools', build this output.
            {'External_Tools': {
                'External_Tools::Production_Tools': {
                    'External_Tools::Production_Tools::Proxy Tools': {}}}}
            """
            split = category.split('::')
            current = categories
            for index in range(len(split)):
                name = '::'.join(split[: index + 1])
                current = current.setdefault(name, {})

        def loadProperties(xml, data):
            def getPropertyFromXML(retKey, propertyKey=None, cast=None):
                if propertyKey is None:
                    propertyKey = retKey
                value = xml.findProperty(propertyKey)
                if value:
                    if cast is not None:
                        value = cast(value)
                    data[retKey] = value
                    return value

            category = getPropertyFromXML('category')
            if category:
                addToolCategory(category)
            getPropertyFromXML('src')
            # Convert the xml string to a bool object
            getPropertyFromXML('disabled', cast=lambda i: i.lower() == 'true')
            getPropertyFromXML('displayName')
            getPropertyFromXML('icon')
            getPropertyFromXML('tooltip', 'toolTip')
            getPropertyFromXML('wiki')

            types = xml.attribute('type')
            if types:
                data['types'] = types
            version = xml.attribute('version')
            if version:
                data['version'] = version
            return data

        def normalizePath(path):
            """ Remove the environment path and normalize the paths for all os
            """
            relPath = os.path.relpath(path, self.environment().path())
            return relPath.replace('\\', '/')

        def getXMLData(toolPath):
            toolPath = os.path.normpath(toolPath)
            doc = blurdev.XML.XMLDocument()
            if doc.load(toolPath) and doc.root():
                xml = doc.root()
                toolFolder = os.path.dirname(toolPath)
                toolId = os.path.basename(toolFolder)
                ret = OrderedDict(name=toolId, path=normalizePath(toolFolder),)
                ret = loadProperties(xml, ret)
                return ret

        if not legacy:
            paths = glob.glob(os.path.join(path, '*', '__meta__.xml'))
            for toolPath in paths:
                toolInfo = getXMLData(toolPath)
                if toolInfo:
                    tools.append(toolInfo)
        else:
            paths = glob.glob(os.path.join(path, '*.*'))
            xmls = set([p for p in paths if os.path.splitext(p)[-1] == '.xml'])
            for toolPath in paths:
                basename, ext = os.path.splitext(toolPath)
                # Don't worry about case in file extension checks
                ext = ext.lower()
                if ext not in ('.ms', '.mse', '.mcr', '.py', '.pyw', '.lnk'):
                    # Not a valid file extension
                    continue

                ret = OrderedDict(
                    legacy=True,  # We have to handle the path of legacy tools differently
                    icon='icon.png',
                    src='../{}'.format(os.path.basename(toolPath)),
                    path=normalizePath(os.path.dirname(toolPath)),
                    category=categoryId,
                )
                toolId = os.path.splitext(os.path.basename(toolPath))[0]
                # Automatically populate legacy settings based on file extension
                if ext in ('.ms', '.mse', '.mcr'):
                    toolId = 'LegacyStudiomax::{}'.format(toolId)
                    ret['types'] = 'LegacyStudiomax'
                elif ext in ('.py', '.pyw'):
                    ret['types'] = (
                        'LegacyExternal'
                        if 'External_Tools' in toolPath
                        else 'LegacySoftimage'
                    )
                    toolId = '{}::{}'.format(ret['types'], toolId)
                    if ret['types'] == 'LegacyExternal':
                        ret['icon'] = 'img/icon.png'
                elif ext == '.lnk':
                    toolId = 'LegacyExternal::{}'.format(toolId)
                    ret['types'] = 'LegacyExternal'

                ret['name'] = toolId
                # Update with data in the tool's xml file if found
                xmlPath = '{}.xml'.format(basename)
                if xmlPath in xmls:
                    doc = blurdev.XML.XMLDocument()
                    if doc.load(xmlPath) and doc.root():
                        xml = doc.root()
                        ret = loadProperties(xml, ret)
                # Always store the toolCategory
                if ret['category']:
                    addToolCategory(ret['category'])
                tools.append(ret)

        # add subcategories
        subpaths = glob.glob(path + '/*/')
        for path in subpaths:
            # isResource = os.path.split(path)[0].endswith('_resource')
            # isMeta = path + '__meta__.xml' in processed
            # if not (isResource or isMeta):
            if not os.path.split(path)[0].endswith('_resource'):
                self.rebuildPathJson(path, categories, tools, legacy, categoryId)

    def rebuildPath(
        self,
        path,
        categories,
        tools,
        legacy=False,
        parentCategoryId='',
        foldername=None,
    ):
        """ rebuilds the tool information recursively for the inputed path and tools
            
            :param path: str
            :param parent: <blurdev.XML.XMLElement>
            :param tools: <blurdev.XML.XMLElement>
            :param legacy: bool
            :param parentCategoryId: str
        """

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
                    categories.add(categoryId)
                node.setAttribute('category', categoryId)
            else:
                logging.error('Error loading tool: {}'.format(toolPath))

        def processLegacyXmlFiles(script, node, categoryId, xmls):
            """ If a matching xml file exists add its contents to the index """
            # Note: If there is a python and maxscript tool with the same name, this xml will be applied to both of them.
            toolPath = '{}.xml'.format(os.path.splitext(script)[0])
            if toolPath in xmls:
                copyXmlData(toolPath, toolIndex, categoryId)

        # If the folder name was not passed in, use the current directory.
        if foldername == None:
            foldername = os.path.normpath(path).split(os.path.sep)[-1].strip('_')
        if parentCategoryId:
            categoryId = parentCategoryId + '::' + foldername
        else:
            categoryId = foldername

        categoryId = '::'.join([split.strip('_') for split in categoryId.split('::')])

        # create a category
        categories.add(categoryId)

        # add non-legacy tools
        processed = []
        if not legacy:
            paths = glob.glob(path + '/*/__meta__.xml')

            for toolPath in paths:
                toolId = os.path.normpath(toolPath).split(os.path.sep)[-2]
                toolIndex = tools.addNode('tool')
                toolIndex.setAttribute('name', toolId)
                toolIndex.setAttribute('category', categoryId)
                # NOTE: renamed to path in json file.
                toolIndex.setAttribute(
                    'loc', self.environment().stripRelativePath(toolPath)
                )

                copyXmlData(toolPath, toolIndex, categoryId)

                processed.append(toolPath)

        # add legacy tools
        else:
            # add maxscript legacy tools
            scripts = glob.glob(os.path.join(path, '*.ms'))
            scripts.extend(glob.glob(os.path.join(path, '*.mse')))
            scripts.extend(glob.glob(os.path.join(path, '*.mcr')))
            xmls = set(glob.glob(os.path.join(path, '*.xml')))
            for script in scripts:
                toolId = os.path.splitext(os.path.basename(script))[0]
                toolIndex = tools.addNode('legacy_tool')
                toolIndex.setAttribute('category', categoryId)
                toolIndex.setAttribute('name', 'LegacyStudiomax::%s' % toolId)
                toolIndex.setAttribute('src', script)
                toolIndex.setAttribute('type', 'LegacyStudiomax')
                toolIndex.setAttribute('icon', 'icon.png')
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
                        toolIndex.setAttribute('icon', 'icon.png')
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
                self.rebuildPath(path, categories, tools, legacy, categoryId)

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
        showDisabled = blurdev.activeEnvironment().showDisabledTools
        return [
            tool
            for tool in self._toolCache.values()
            if tool.isFavorite()
            and tool.favoriteGroup() == None
            and (showDisabled or not tool.disabled())
        ]

    def filename(self, **kwargs):
        """ returns the filename for this index
        """
        return self.environment().relativePath('tools.json')

    def load(self, toolId=None):
        """ loads the current index from the system.

        Args:
            toolId (str or None, optional): If provided, then only the tool
                who's name matches this string will be added to the index.
                This allows us to speed up one off tool lookups. If used,
                then the tools index will not be cached.
        """
        if not self._loaded:
            filename = self.filename()
            from blurdev.tools.toolscategory import ToolsCategory
            from blurdev.tools.tool import Tool

            # Setting _loaded to True, makes sure that when each Tool object we
            # create does not end triggering a call to load()
            self._loaded = True

            if not os.path.exists(filename):
                return

            with open(filename) as f:
                indexJson = json.load(f)

            # load categories
            categories = indexJson.get('categories', {})
            for topLevelCategory in categories:
                ToolsCategory.fromIndex(
                    self,
                    self,
                    name=topLevelCategory,
                    children=categories[topLevelCategory],
                )

            # load tools
            tools = indexJson.get('tools', [])
            loadAllTools = toolId is None
            for tool in tools:
                if not loadAllTools and tool['name'] != toolId:
                    continue
                Tool.fromIndex(self, tool)
            # If a toolId was passed in, we should not consider the tools index loaded.
            # This would make it impossible to access any other tools
            self._loaded = loadAllTools

    def loadFavorites(self):
        if not self._favoritesLoaded:
            if not os.path.exists(self.filename()):
                # If the tools index does not exist, then actually loading
                # favorites accomplishes nothing, and if _favoritesLoaded
                # is True, saveFavorites will end up erasing all favorites.
                # Users tend to get annoyed by that "feature", so don't do it.
                return
            # For favorites to work, we need to load the entire environment
            # index, not just each tool we are using for favorites, which is
            # the default behavior of self.findTool, if load is not called.
            self.load()
            self._favoritesLoaded = True
            # load favorites
            pref = blurdev.prefs.find('treegrunt/favorites')
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
        self.load(name)
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

    def findToolsByRedistributable(self, state):
        """ Return a list of tools with redistributable set to the provided boolean value """
        return [
            tool
            for tool in blurdev.activeEnvironment().index().tools()
            if tool.redistributable() == state
        ]

    def saveFavorites(self):
        # load favorites
        if self._favoritesLoaded:
            pref = blurdev.prefs.find('treegrunt/favorites')
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
        try:
            expr = re.compile(str(searchString).replace('*', '.*'), re.IGNORECASE)
        except re.error:
            # a invalid search string was provided, return a empty list
            return []
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
