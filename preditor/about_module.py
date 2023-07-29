from __future__ import absolute_import

import abc
import os
import sys
import textwrap

import six
from future.utils import with_metaclass

import preditor


class AboutModule(with_metaclass(abc.ABCMeta, object)):
    """Base class for the `preditor.plug.about_module` entry point. Create a
    subclass of this method and expose the class object to the entry point.

    Properties:
        instance: If provided, the instance of PrEditor to generate text for.
    """

    indent = "  "
    """Use this to indent new lines for text"""

    def __init__(self, instance=None):
        self.instance = instance

    @classmethod
    def generate(cls, instance=None):
        """Generates the output text for all plugins.

        Outputs this for each plugin:

            {name}: {version}
            {indent}{text line 1}
            {indent}{text line ...}

        Name is the name of each entry point. If duplicates are found, a logging
        warning is generated. Each line of `self.text()` is indented
        """
        ret = []
        for name, plugin in preditor.plugins.about_module():
            version = "Unknown"
            if isinstance(plugin, str):
                text = plugin
            else:
                try:
                    plug = plugin(instance=instance)
                    if not plug.enabled():
                        continue
                    version = plug.version()
                    text = plug.text()
                except Exception as error:
                    text = "Error processing: {}".format(error)
            if six.PY3:
                text = textwrap.indent(text, cls.indent)
            else:
                text = ['{}{}'.format(cls.indent, line) for line in text.split('\n')]
                text = "\n".join(text)

            # Build the output string including the version information if provided.
            if version is not None:
                ret.append("{}: {}\n{}".format(name, version, text))
            else:
                ret.append("{}:\n{}".format(name, text))

        return '\n'.join(ret)

    def enabled(self):
        """The plugin can use this to disable reporting by generate."""
        return True

    @abc.abstractmethod
    def text(self):
        """Returns info about this plugin. This can have multiple lines, and
        each line will be indented to provide visual distinction between plugins.
        """

    @abc.abstractmethod
    def version(self):
        """Returns The version as a string to show next to name."""


class AboutPreditor(AboutModule):
    """About module used to show info about PrEditor."""

    def text(self):
        """Return the path PrEditor was loaded from for quick debugging."""
        ret = []
        # Include the core_name of the current PrEditor gui instance if possible
        if self.instance:
            ret.append("Core Name: {}".format(self.instance.name))
        # THe path to the PrEditor package
        ret.append("Path: {}".format(os.path.dirname(preditor.__file__)))
        return "\n".join(ret)

    def version(self):
        return preditor.__version__


class AboutQt(AboutModule):
    """Info about Qt modules being used."""

    def text(self):
        """Return the path PrEditor was loaded from for quick debugging."""
        from Qt import QtCore, __binding__, __version__

        ret = ['Qt.py: {}, binding: {}'.format(__version__, __binding__)]

        # Attempt to get a version for QtSiteConfig if defined
        try:
            import QtSiteConfig

            ret.append('QtSiteConfig: {}'.format(QtSiteConfig.__version__))
        except (ImportError, AttributeError):
            pass

        # Add info for all Qt5 bindings that have been imported
        if 'PyQt5.QtCore' in sys.modules:
            ret.append('PyQt5: {}'.format(sys.modules['PyQt5.QtCore'].PYQT_VERSION_STR))
        if 'PySide2.QtCore' in sys.modules:
            ret.append('PySide2: {}'.format(sys.modules['PySide2.QtCore'].qVersion()))

        # Add qt library paths for plugin debugging
        for i, path in enumerate(QtCore.QCoreApplication.libraryPaths()):
            if i == 0:
                ret.append('Library Paths: {}'.format(path))
            else:
                ret.append('               {}'.format(path))

        return "\n".join(ret)

    def version(self):
        from Qt import __qt_version__

        return __qt_version__


class AboutPython(AboutModule):
    """Info about the current instance of python."""

    def text(self):
        """Return the path PrEditor was loaded from for quick debugging."""
        ret = sys.version
        # Windows doesn't add a newline before the compiler info, and it can end
        # up being a little long for QMessageBox's with short file paths. Add
        # the newline like is present on linux
        ret = ret.replace(") [", ")\n[")
        return ret

    def version(self):
        return '{}.{}.{}'.format(*sys.version_info[:3])


class AboutExe(AboutModule):
    """The value of sys.executable, disabled if not set."""

    def enabled(self):
        return bool(sys.executable)

    def text(self):
        return sys.executable

    def version(self):
        """No version is returned for this class."""
        return None
