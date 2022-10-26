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
    """

    indent = "  "
    """Use this to indent new lines for text"""

    @classmethod
    def generate(cls):
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
                    instance = plugin()
                    if not instance.enabled():
                        continue
                    version = instance.version()
                    text = instance.text()
                except Exception as error:
                    text = "Error processing: {}".format(error)
            if six.PY3:
                text = textwrap.indent(text, cls.indent)
            else:
                text = ['{}{}'.format(cls.indent, line) for line in text.split('\n')]
                text = "\n".join(text)
            ret.append("{}: {}\n{}".format(name, version, text))

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
        return os.path.dirname(preditor.__file__)

    def version(self):
        return preditor.__version__


class AboutQt(AboutModule):
    """Info about Qt modules being used."""

    def text(self):
        """Return the path PrEditor was loaded from for quick debugging."""
        from Qt import __binding__, __version__

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
