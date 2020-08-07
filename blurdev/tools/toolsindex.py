from __future__ import absolute_import

import os
import re
import functools
import glob
import logging
import shutil
import tempfile
from difflib import SequenceMatcher

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


logger = logging.getLogger(__name__)


class ToolsIndex(QObject):
    """ Defines the indexing system for the tools package
    """

    def __init__(self, environment):
        super(ToolsIndex, self).__init__(environment)
        self._loaded = False
        self._favoritesLoaded = False
        self._categoryCache = {}
        self._toolCache = {}
        self._entry_points = []
        self._loaded_entry_points = False
        self._tool_root_paths = []

    def baseCategories(self):
        """ returns the categories that are parented to this index
        """
        self.load()
        output = [cat for cat in self._categoryCache.values() if cat.parent() == self]
        output.sort(key=lambda x: x.objectName())
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
        self._entry_points = []
        self._loaded_entry_points = False

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
        output.sort(key=lambda x: x.objectName())
        return output

    def cacheCategory(self, category):
        """ caches the category
        """
        self._categoryCache[str(category.objectName())] = category

    def cacheTool(self, tool):
        """ caches the inputed tool by its name
        """
        self._toolCache[str(tool.objectName())] = tool

    def entry_points(self):
        """ A list of entry point data resolved when the index was last rebuilt.

        Each item is a list with the name, module_name, and args of a resolved
        `blurdev.tools.paths` entry point.
        """
        if not self._loaded_entry_points:
            filename = self.filename(filename='entry_points.json')
            # Build the entry_points file if it doesn't exist
            if not os.path.exists(filename):
                try:
                    self._rebuild_entry_points()
                except IOError as error:
                    logger.info(error)
                    return []

            with open(filename) as f:
                self._entry_points = json.load(f)

            # load entry_points
            self._loaded_entry_points = True

        return self._entry_points

    def environment(self):
        """ returns this index's environment
        """
        return self.parent()

    def rebuild(self, filename=None, configFilename=True):
        """ rebuilds the index from the file system.

        This does not create any necessary directory structure to save the files.

        Args:
            filename (str): If filename is not provided it will store the file in
                self.filename(). This is the location that treegrunt looks for its
                tools.xml file.
            configFilename (str|bool): if True, save as config.ini next to filename. If
                a file path is provided save to that file path.

        """

        # Update the entry_points.json file.
        self._rebuild_entry_points()

        # Now that the entry_points.json file is updated, reload the treegrunt
        # environment so we resolve any entry point changes made sense the last
        # index rebuild. Without this, you would need to rebuild, reload, and
        # rebuild to fully update the index.
        self.environment().resetPaths()

        # If a filename was not provided get the default
        if not filename:
            filename = self.filename()

        first_build = not os.path.exists(filename)

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

        if first_build:
            # If this is the first time the index is being built, we need to fully load
            # the environment and rebuild the index again. If we don't then the index
            # will be missing the tools added in virtualenv entry points.
            logger.info(
                'This was the first index rebuild, rebuilding a second time is required'
            )
            self.rebuild(filename=filename, configFilename=configFilename)

    def _rebuild_entry_points(self):
        """ Update the entry_points definitions for this environment.

        Creates a new pkg_resources.WorkingSet object to search for any
        'blurdev.tools.paths' entry points and stores that info in
        entry_points.json next to the environment index file.

        Blurdev's TREEGRUNT_ROOT entry point is sorted to the start because the other
        entry points most likely are not importable unless TREEGRUNT_ROOT is processed.
        No other sorting of entry_points is done so load order is not guaranteed. The
        order saved in the entry_points.json file will be used until the next rebuild.

        Raises:
            IOError: The treegrunt root directory used to store entry_points.json
                does not exist.
        """

        filename = self.filename(filename='entry_points.json')
        dirname, basename = os.path.split(filename)
        if not os.path.exists(dirname):
            raise IOError(2, 'Treegrunt root does not exist: "{}"'.format(dirname))

        entry_points = []

        # importing pkg_resources takes ~0.8 seconds only import it if we need to.
        import pkg_resources

        # Make our own WorkingSet. The cached pkg_resources WorkingSet doesn't get
        # updated by blurdev's environment refresh.
        packages = pkg_resources.WorkingSet()
        entries = packages.iter_entry_points('blurdev.tools.paths')
        for entry_point in entries:
            entry_points.append(
                [entry_point.name, entry_point.module_name, entry_point.attrs]
            )

        # Ensure that the blurdev's entry point is processed first, we need to add
        # its paths before we try to load any of the other entry_points that are
        # likely being loaded from the blurdev entry point.
        entry_points.sort(key=lambda a: -1 if a[0] == 'TREEGRUNT_ROOT' else 1)

        name, extension = os.path.splitext(basename)
        with tempfile.NamedTemporaryFile(
            mode='w+', prefix=name, suffix=extension
        ) as fle:
            json.dump(entry_points, fle, indent=4)
            fle.seek(0)
            with open(filename, 'w') as out:
                shutil.copyfileobj(fle, out)

    def _rebuildJson(self, filename):
        categories = {}
        tools = []

        for path, legacy in self.toolRootPaths():
            self.rebuildPathJson(path, categories, tools, legacy=legacy)

        # Use OrderedDict to build this so the json is saved consistently.
        dirname, basename = os.path.split(filename)
        output = OrderedDict(categories=categories)
        output['tools'] = tools
        name, extension = os.path.splitext(basename)

        # Generating JSON index in a temporary location.
        # Once successfully generated we will copy the file where it needs to go.
        with tempfile.NamedTemporaryFile(
            mode='w+', prefix=name, suffix=extension
        ) as fle:
            json.dump(output, fle, indent=4)
            fle.seek(0)
            with open(filename, 'w') as out:
                shutil.copyfileobj(fle, out)

            # Copying the tool index to the orignal location for backwards
            # compatibility. Essentially host that will have the old blurdev will still
            # look in the old place.
            # TODO: Remove this block once everyone has versions 2.11.0.
            if os.path.exists(os.path.join(dirname, 'code')):
                # The read head is at the end of the file, move it back to the start of
                # the file so we can copy it again.
                fle.seek(0)
                with open(os.path.join(dirname, 'code', basename), 'w') as out:
                    shutil.copyfileobj(fle, out)

    def rebuildPathJson(
        self, path, categories, tools, legacy=False, parentCategoryId=None
    ):

        if not os.path.exists(path):
            logger.debug('Unable to add tools in: "{}"'.format(path))
            return

        isdir = os.path.isdir(path)

        def addToolCategory(category):
            """ Update the categories dict to include this category

            if passed 'External_Tools::Production_Tools::Proxy Tools', build this
            output.

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
            getPropertyFromXML('cliModule')

            types = xml.attribute('type')
            if types:
                data['types'] = types
            version = xml.attribute('version')
            if version:
                data['version'] = version
            return data

        def getXMLData(toolPath):
            toolPath = os.path.normpath(toolPath)
            doc = blurdev.XML.XMLDocument()
            if doc.load(toolPath) and doc.root():
                xml = doc.root()
                toolFolder = os.path.dirname(toolPath)
                toolId = os.path.basename(toolFolder)
                ret = OrderedDict(name=toolId, path=toolFolder,)
                ret = loadProperties(xml, ret)
                return ret

        if not legacy:
            if isdir:
                # Find all __meta__.xml files in sub-directories of the directory
                paths = glob.glob(os.path.join(path, '*', '__meta__.xml'))
            else:
                # A __meta__.xml file was directly given, no need to glob
                paths = [path]
            for toolPath in paths:
                toolInfo = getXMLData(toolPath)
                if toolInfo:
                    tools.append(toolInfo)
        else:
            # Calculate recursive folder names for legacy tools structure
            foldername = os.path.normpath(path)
            if not isdir:
                foldername = os.path.dirname(foldername)
            foldername = os.path.basename(foldername).strip('_')

            if parentCategoryId:
                categoryId = parentCategoryId + '::' + foldername
            else:
                categoryId = foldername

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
                    # We have to handle the path of legacy tools differently.
                    legacy=True,
                    icon='icon.png',
                    src='../{}'.format(os.path.basename(toolPath)),
                    path=os.path.dirname(toolPath),
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
                if not os.path.split(path)[0].endswith('_resource'):
                    self.rebuildPathJson(path, categories, tools, legacy, categoryId)

    def reload(self):
        """Reload the index without rebuilding it. This will allow users to refresh the
        index without restarting treegrunt."""
        self.clear()
        self.load()
        self.loadFavorites()

    @classmethod
    def resolve_entry_point(cls, entry_point):
        """
        Resolve the entry point from its module and attrs.

        This replicates parts of the pkg_resources system. We are not using it
        here because importing pkg_resources takes time and we also need to
        rebuild its index when switching treegrunt environments.
        """
        # Copied from the `pkg_resources.EntryPoint.resolve` function
        module = __import__(entry_point[1], fromlist=['__name__'], level=0)
        try:
            return functools.reduce(getattr, entry_point[2], module)
        except AttributeError as exc:
            raise ImportError(str(exc))

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
        return [tool for tool in self._toolCache.values() if tool.isFavorite()]

    def filename(self, **kwargs):
        """ returns the filename for this index

        Args:
            filename (str, optional): Use this filename instead of the default
                `tools.json`.
        """
        filename = kwargs.get('filename', 'tools.json')
        return self.environment().relativePath(filename)

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
        """ returns the tool based on the inputed name, returning the default option if
        no tool is found
        """
        self.load()
        return self._categoryCache.get(str(name))

    def findTool(self, name):
        """ returns the tool based on the inputed name, returning the default option if
        no tool is found
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
        output.sort(key=lambda x: x.objectName().lower())
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

        output.sort(key=lambda x: x.name().lower())

        return output

    def findToolsByRedistributable(self, state):
        """ Return a list of tools with redistributable set to the provided boolean
        value """
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

        This function implements a fuzzy search. The name matches if the characters
        in the search string appear in the same order in the tool name.

        """
        self.load()
        output = []
        try:
            # Remove "junk" characters for the regex
            searchString = searchString.replace('*', '')
            searchString = searchString.replace(' ', '')
            # Put a wildcard between every character of the search string
            expr = re.compile('.*'.join(searchString), re.IGNORECASE)
        except re.error:
            return []

        # SequenceMatcher.ratio() gives a value of how close a match the
        # strings are, 1.0 being an exact match. Use that to order the matches
        sm = SequenceMatcher()
        sm.set_seq2(searchString)
        for tool in self._toolCache.values():
            if expr.search(tool.displayName()):
                sm.set_seq1(tool.displayName())
                output.append((tool, sm.ratio()))

        output.sort(key=lambda x: x[1], reverse=True)
        output = [i[0] for i in output]

        return output

    def tools(self):
        return self._toolCache.values()

    def toolNames(self):
        return self._toolCache.keys()

    def toolRootPaths(self):
        """ A list of paths to search for tools when rebuild is called.

        Each item in this list should be a list/tuple of the path to search for tools
        and a bool to indicate if its a legacy tool structure.
        """
        return self._tool_root_paths

    def setToolRootPaths(self, paths):
        self._tool_root_paths = paths
