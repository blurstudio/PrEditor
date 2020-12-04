from distutils import log
from setuptools import Command
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from blurdev.tools.toolsindex import ToolsIndex


class _ToolsIndex(Command):
    """ Builds the treegrunt index for the provided entry_point information.
    This class should not be used directly, but sub-classed by the buildCmdFactory
    function. This is required because each setup.py needs to set its own tools_package
    data and setuptools requires passing a class not a instance to cmdclass.
    """

    description = 'Build a tregrunt index file for this pip package.'
    user_options = []

    def initialize_options(self):
        """Set default values for options."""
        # Nothing to set, but must be overridden by sub-classes

    def finalize_options(self):
        """Post-process options."""
        # Nothing to set, but must be overridden by sub-classes

    def run(self):
        try:
            # self.tools_package is not defined by default on this class so we can
            # enforce it being set by a subclass.
            tools_package = self.tools_package
        except AttributeError:
            raise RuntimeError(
                'You can not use _BaseDevelopToolsIndex directly, it must be '
                'subclassed by the buildCmdFactory function.'
            )

        log.info('Blurdev: Building the treegrunt tools index for this pip package')
        # tools_package is created by the buildCmdFactory function.
        ToolsIndex.buildIndexForToolsPackage(tools_package)


class BaseBuildToolsIndex(build_py):
    """ Override of build_py that calls the tools_index build command. """

    def run(self):
        self.run_command('tools_index')
        # Super call to run the normal wheel build
        build_py.run(self)


class BaseDevelopToolsIndex(develop):
    """ Override of develop that calls the tools_index build command. """

    def run(self):
        self.run_command('tools_index')
        # Super call to run the normal wheel build
        develop.run(self)


def buildCmdFactory(tools_package, additional=None):
    """ Creates a few cmdclass overrides that automatically builds a treegrunt tool
    index file.

    This class adds the tools_index command and updates the the setuptools build_py and
    develop commands with ones that call tools_index.

    Args:
        tools_package: The entry point information used to find the and run this pip
            packages treegrunt index method. Takes a list that can be used to
            instantiate a :py:class:`blurdev.tools.toolspackage.ToolsPackage` object
            or a instance of that class.
        additional (dict, optional): The build_py and develop commands will be updated
            onto this dictionary if passed.

    Returns:
        dict: A dict that can be passed to the cmdclass argument of setup.

    Example::

        from blurdev.tools.setup_tools import buildCmdFactory
        setup(
            cmdclass=buildCmdFactory(["trax", "trax.tools", ["tool_paths"]])
            ...
        )
    """
    if additional is None:
        additional = {}
    # We can't pass a instance of the command class, so we create a new class that
    # stores the tools_package as a class property.
    tools_index = type(
        'ToolsIndex', (_ToolsIndex, object), {'tools_package': tools_package}
    )

    additional.update(
        {
            'build_py': BaseBuildToolsIndex,
            'develop': BaseDevelopToolsIndex,
            'tools_index': tools_index,
        }
    )
    return additional
