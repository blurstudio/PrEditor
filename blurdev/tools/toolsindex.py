from __future__ import absolute_import

import os
import re
import sys
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
from collections import OrderedDict
from .toolscategory import ToolsCategory
from .tool import Tool
from .toolspackage import ToolsPackage


logger = logging.getLogger(__name__)


class ToolsIndex(QObject):
    """ Defines the indexing system for the tools package
    """

    def __init__(self, environment):
        super(ToolsIndex, self).__init__(environment)
        self._loaded = False
        self._favorite_tool_ids = set()
        self._favoritesLoaded = False
        self._categoryCache = {}
        self._toolCache = {}
        self._packages = []
        self._loaded_packages = False
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
        self._packages = []
        self._loaded_packages = False

        # remove all the children
        for child in self.findChildren(Tool):
            child.setParent(None)
            child.deleteLater()

        for child in self.findChildren(ToolsCategory):
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

    def editable_install_paths(self):
        """ Generates a set of all paths contained in all .egg-link files on sys.path
        """
        repo_roots = set()
        for path in sys.path:
            for link in glob.glob(os.path.join(path, '*.egg-link')):

                for line in open(link).readlines():
                    line = line.strip()
                    if line != '.' and os.path.exists(line):
                        repo_roots.add(line)
        return repo_roots

    def editable_tools_package_ids(self):
        """ Returns the name and module_name for editable blurdev.tools.paths installs.
        """
        # importing pkg_resources takes ~0.8 seconds only import it if we need to.
        import pkg_resources

        editable = set()
        for path in self.editable_install_paths():
            # Note: pkg_resources.find_distributions is not dependent on the working set
            for dist in pkg_resources.find_distributions(path):
                entries = dist.get_entry_map('blurdev.tools.paths')
                editable.update(
                    {(entry.name, entry.module_name) for entry in entries.values()}
                )
        return editable

    def packages(self):
        """ A list of entry point data resolved when the index was last rebuilt.

        Each item is a list with the name, module_name, and args of a resolved
        `blurdev.tools.paths` entry point.
        """
        if not self._loaded_packages:
            filename = self.filename(filename='entry_points.json')
            # Build the entry_points file if it doesn't exist
            if not os.path.exists(filename):
                try:
                    self._rebuild_entry_points()
                except IOError as error:
                    logger.info(error)
                    return []

            with open(filename) as f:
                entry_points = json.load(f)
                self._packages = []
                for entry_point in entry_points:
                    tools_package = ToolsPackage(entry_point)
                    self._packages.append(tools_package)

            self._loaded_packages = True

        return self._packages

    def environment(self):
        """ returns this index's environment
        """
        return self.parent()

    def rebuild(self, filename=None, configFilename=True, path_replace=None):
        """ rebuilds the index from the file system.

        This does not create any necessary directory structure to save the files.

        Tools packages are found by processing the `blurdev.tools.paths` entry_point.
        The first item in the entry point list(the name) is used as a unique identifier
        and the last processed entry_point is used if there are duplicate names. If you
        need to add entry points that are not currently installed you can add them with
        a json string stored in the ``BDEV_TOOLS_INDEX_DEFAULT_ENTRY_POINTS``
        environment variable. These are processed before the entry points found by
        pkg_resources. This is used to add the trax tools package on our release
        environments. These have to be built without trax installed due to how trax is
        distributed on each host but the release environments are shared on the network.

        Example::

            set BDEV_TOOLS_INDEX_DEFAULT_ENTRY_POINTS=[["name", "module", ["function"]]]

        Args:
            filename (str): If filename is not provided it will store the file in
                self.filename(). This is the location that treegrunt looks for its
                tools.xml file.
            configFilename (str|bool): if True, save as config.ini next to filename. If
                a file path is provided save to that file path.
            path_replace (tuple, optional): If provided, call str.replace with these
                arguments on each tool's path stored in the index file.
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
        self._rebuildJson(filename=filename, path_replace=path_replace)
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
            self.rebuild(
                filename=filename,
                configFilename=configFilename,
                path_replace=path_replace,
            )

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

        entry_points = {}

        # When building the release environments we don't have access to all pip
        # packages in the virtualenv. For example trax is installed on the local
        # computer not in the release environment. This lets us manually add the
        # extra entry_point cache when building the treegrunt environment.
        defaults = os.getenv('BDEV_TOOLS_INDEX_DEFAULT_ENTRY_POINTS')
        if defaults:
            defaults = json.loads(defaults)
            entry_points = {ep[0]: ep for ep in defaults}

        # importing pkg_resources takes ~0.8 seconds only import it if we need to.
        import pkg_resources

        # Make our own WorkingSet. The cached pkg_resources WorkingSet doesn't get
        # updated by blurdev's environment refresh.
        packages = pkg_resources.WorkingSet()
        entries = packages.iter_entry_points('blurdev.tools.paths')
        for entry_point in entries:
            entry_points[entry_point.name] = [
                entry_point.name,
                entry_point.module_name,
                entry_point.attrs,
            ]

        # Convert the dict to a list for saving: We use a dictionary so we can use the
        # entry point name to ensure unique values especially when using the
        # environment variable.
        entry_points = entry_points.values()

        # Ensure that the blurdev's entry point is processed first, we need to add
        # its paths before we try to load any of the other entry_points that are
        # likely being loaded from the blurdev entry point.
        entry_points = sorted(
            entry_points, key=lambda a: -1 if a[0] == 'TREEGRUNT_ROOT' else 1
        )

        name, extension = os.path.splitext(basename)
        with tempfile.NamedTemporaryFile(
            mode='w+', prefix=name, suffix=extension
        ) as fle:
            json.dump(entry_points, fle, indent=4)
            fle.seek(0)
            with open(filename, 'w') as out:
                shutil.copyfileobj(fle, out)

    def _rebuildJson(self, filename, path_replace=None):
        categories = {}
        tools = []

        editable_ids = self.editable_tools_package_ids()
        for package in self.packages():
            if not package.tool_index():
                logger.info('tool_index for "{}" added to shared index'.format(
                    package.name())
                )
                for tool_path in package.tool_paths():
                    # If legacy wasn't passed we can assume its not a legacy
                    # file structure
                    if isinstance(tool_path, str):
                        tool_path = [tool_path, False]

                    self.rebuildPathJson(
                        tool_path[0],
                        categories,
                        tools,
                        legacy=tool_path[1],
                        path_replace=path_replace,
                    )
            elif (package.name(), package.module_name()) in editable_ids:
                # This package with a tools_index is a editable install and we should
                # rebuild the index.
                logger.info(
                    'tool_index for "{}" generated for editable install'.format(
                        package.name()
                    )
                )
                self.buildIndexForToolsPackage(package)

        self.saveToolJson(filename, categories, tools)

    @classmethod
    def buildIndexForToolsPackage(cls, package):
        if isinstance(package, (list, tuple)):
            package = ToolsPackage(package)

        categories = {}
        tools = []

        filename = package.tool_index()
        if not filename:
            logging.debug('No tool_index defined for {}'.format(package.name()))
            return None, categories, tools

        relative_root = os.path.dirname(filename)

        for tool_path in package.tool_paths():
            # If legacy wasn't passed we can assume its not a legacy file structure
            if isinstance(tool_path, str):
                tool_path = [tool_path, False]

            cls.rebuildPathJson(
                tool_path[0],
                categories,
                tools,
                legacy=tool_path[1],
                relative_root=relative_root,
            )

        cls.saveToolJson(filename, categories, tools)
        return filename, categories, tools

    @classmethod
    def saveToolJson(cls, filename, categories, tools):

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

    @classmethod
    def rebuildPathJson(
        cls,
        path,
        categories,
        tools,
        legacy=False,
        parentCategoryId=None,
        path_replace=None,
        relative_root=None,
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
                tool_folder = os.path.dirname(toolPath)
                toolId = os.path.basename(tool_folder)
                if path_replace is not None:
                    tool_folder = tool_folder.replace(*path_replace)
                if relative_root:
                    tool_folder = os.path.relpath(tool_folder, relative_root)
                ret = OrderedDict(name=toolId, path=tool_folder,)
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

                tool_folder = os.path.dirname(toolPath)
                if path_replace is not None:
                    tool_folder = tool_folder.replace(*path_replace)

                ret = OrderedDict(
                    # We have to handle the path of legacy tools differently.
                    legacy=True,
                    icon='icon.png',
                    src='../{}'.format(os.path.basename(toolPath)),
                    path=tool_folder,
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
                    cls.rebuildPathJson(
                        path,
                        categories,
                        tools,
                        legacy,
                        categoryId,
                        path_replace=path_replace,
                    )

    def reload(self):
        """Reload the index without rebuilding it. This will allow users to refresh the
        index without restarting treegrunt."""
        self.clear()
        self.load()
        self.loadFavorites()

    def favoriteToolIds(self):
        """ The tool id's the user has favorited.

        This is stored as a set of tool ids so we can store tool ids that are not valid
        for the current treegrunt environment. This allows you to keep your favorites
        when you switch between multiple treegrunt environments even if they don't have
        the same treegrunt tools. This does mean that as we remove old tools, they won't
        get removed from peoples saved favorites, but this is better than a user loosing
        their favorites because the index didn't build, or they switched to an
        environment that doesn't have their tool.
        """
        self.loadFavorites()
        return self._favorite_tool_ids

    def favoriteTools(self):
        """ Returns a list of ``blurdev.tools.Tool`` that the user has favorited.
        """
        ret = []
        for tool_id in self.favoriteToolIds():
            tool = self._toolCache.get(str(tool_id))
            if tool:
                ret.append(tool)
        return ret

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
            load_all = toolId is None
            self.loadIndexFile(filename, toolId=toolId, load_all=load_all)

            # Handle any entry_point specified index files.
            for tools_package in self.packages():
                if tools_package.tool_index():
                    self.loadIndexFile(
                        tools_package.tool_index(),
                        toolId=toolId,
                        load_all=load_all,
                        relative=True,
                    )
            # Only consider everything loaded if we didn't use a toolId
            # TODO: Refactor how load is called so we don't need to call it everywhere
            # with a self._loaded check.
            self._loaded = load_all

    def loadIndexFile(self, filename, toolId=None, load_all=True, relative=False):
        if not os.path.exists(filename):
            return

        relative_root = os.path.dirname(filename) if relative else None
        # Setting _loaded to True, makes sure that when each Tool object we
        # create does not end triggering a call to load()
        loaded = self._loaded
        self._loaded = True

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
        for tool in tools:
            if not load_all and tool['name'] != toolId:
                continue
            Tool.fromIndex(self, tool, relative_root=relative_root)

        self._loaded = loaded

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
                    # If a user has the old favorite groups pref, skip them,
                    # the next time we save they should be removed.
                    continue
                tool_id = child.attribute('id')
                tool = self.findTool(tool_id)
                if tool.isNull():
                    # This tool is not valid for this index, make sure its added
                    # so it is not lost when saving the favorites to disk.
                    self._favorite_tool_ids.add(tool_id)
                else:
                    # Its a valid tool, let the Tool api update _favorite_tool_ids
                    tool.setFavorite(True)

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
        return self._toolCache.get(str(name), Tool())

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
            regex = re.compile(r'\d')
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

            # record the tools
            for tool_id in sorted(self.favoriteToolIds()):
                node = root.addNode('tool')
                node.setAttribute('id', tool_id)
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
