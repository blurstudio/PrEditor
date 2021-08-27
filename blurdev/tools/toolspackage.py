from __future__ import absolute_import
import functools
import logging

logger = logging.getLogger(__name__)


class ToolsPackage(object):
    """Manages how treegrunt entry points are loaded.

    Args:
        entry_point (list): A valid entry_point definition. Contains the name of the
            entry point, the module that needs imported and attrs for the module
            (the object to call). This list should have 3 items, The name of the entry
            point, the module it requires to be imported, and the function to call.
    """

    def __init__(self, entry_point):
        self.entry_point = entry_point

    def _resolve(self):
        """Resolve the entry point information. This is called automatically
        when required. If called in __init__ module will not resolve correctly.
        """
        logger.debug('Processing entry point: {}'.format(self.entry_point))
        # Attempt to load the module, report errors but don't break the
        # import of blurdev if one of these fail.
        try:
            tool_info = self.function()()
        except Exception:
            # `logging.exception` automatically calls basicConfig if there are no
            # handlers configured. Replicate this here so we can see the exception in
            # the command prompt.

            # TODO: This probably needs to be handled earlier in the blurdev init, but
            # we haven't finalized how we work with logging yet, and this information
            # is very important. However, we need to worry about some of the burner
            # plugins detecting printed tracebacks and 3ds max Batch treating any
            # stderr text written as a failure.
            if len(logging.root.handlers) == 0:
                logging.basicConfig()
            logger.exception('Skipping entry point: {}'.format(self.entry_point))

            # Provide a empty set of defaults
            tool_info = (tuple(), tuple())

        self._sys_paths = tool_info[0]
        self._tool_paths = tool_info[1]
        self._tool_index = None
        if len(tool_info) > 2:
            self._tool_index = tool_info[2]

    def attrs(self):
        """The name of the function to call. This is the 3rd item of the entry point."""
        return self.entry_point[2]

    def function(self):
        """The python function being specified by the entry point."""
        # Copied from the `pkg_resources.EntryPoint.resolve` function
        try:
            return functools.reduce(getattr, self.attrs(), self.module())
        except AttributeError as exc:
            raise ImportError(str(exc))

    def module(self):
        """Imports and returns the python module specified by module_name."""
        # Copied from the `pkg_resources.EntryPoint.resolve` function
        module = __import__(self.module_name(), fromlist=['__name__'], level=0)
        return module

    def module_name(self):
        """The name of the python module that will be imported.
        This is the 2nd item of the entry point.
        """
        return self.entry_point[1]

    def name(self):
        """The name of the entry point. This is the 1st item of the entry point."""
        return self.entry_point[0]

    def sys_paths(self):
        """A list of paths that need added to sys.path to add imports."""
        try:
            return self._sys_paths
        except AttributeError:
            self._resolve()
            return self._sys_paths

    def tool_index(self):
        """The path used to store a tools index specific to the package.

        This is optional and may be set to None. If set this is the path to a json file
        built with :py:meth:`ToolsIndex.buildIndexForToolsPackage` or
        :py:meth:`blurdev.tools.setup_tools.buildCmdFactory`.
        """
        try:
            return self._tool_index
        except AttributeError:
            self._resolve()
            return self._tool_index

    def tool_paths(self):
        """A list of paths treegrunt should scan for tools.

        You can pass directory paths or a specific __meta__.xml file if your package
        only has one tool.
        """
        try:
            return self._tool_paths
        except AttributeError:
            self._resolve()
            return self._tool_paths
