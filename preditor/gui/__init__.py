from __future__ import absolute_import

from functools import partial

from Qt.QtCore import Property

from .dialog import Dialog  # noqa: F401
from .window import Window  # noqa: F401


def QtPropertyInit(name, default, callback=None, typ=None):
    """Initializes a default Property value with a usable getter and setter.

    You can optionally pass a function that will get called any time the property
    is set. If using the same callback for multiple properties, you may want to
    use the preditor.decorators.singleShot decorator to prevent your function getting
    called multiple times at once. This callback must accept the attribute name and
    value being set.

    Example:
        class TestClass(QWidget):
            def __init__(self, *args, **kwargs):
                super(TestClass, self).__init__(*args, **kwargs)

            stdoutColor = QtPropertyInit('_stdoutColor', QColor(0, 0, 255))
            pyForegroundColor = QtPropertyInit('_pyForegroundColor', QColor(0, 0, 255))

    Args:
        name(str): The name of internal attribute to store to and lookup from.
        default: The property's default value.  This will also define the Property type
            if typ is not set.
        callback(callable): If provided this function is called when the property is
            set.
        typ (class, optional): If not None this value is used to specify the type of
            the Property. This is useful when you need to specify a property as python's
            object but pass a default value of a given class.

    Returns:
        Property
    """

    def _getattrDefault(default, self, attrName):
        try:
            value = getattr(self, attrName)
        except AttributeError:
            setattr(self, attrName, default)
            return default
        return value

    def _setattrCallback(callback, attrName, self, value):
        setattr(self, attrName, value)
        if callback:
            callback(self, attrName, value)

    ga = partial(_getattrDefault, default)
    sa = partial(_setattrCallback, callback, name)
    # Use the default value's class if typ is not provided.
    if typ is None:
        typ = default.__class__
    return Property(typ, fget=(lambda s: ga(s, name)), fset=(lambda s, v: sa(s, v)))


def loadUi(filename, widget, uiname=''):
    """use's Qt's uic loader to load dynamic interafces onto the inputed widget

    Args:
        filename (str): The python filename. Its basename will be split off, and a
            ui folder will be added. The file ext will be changed to .ui
        widget (QWidget): The basewidget the ui file will be loaded onto.
        uiname (str, optional): Used instead of the basename. This is useful if
            filename is not the same as the ui file you want to load.
    """
    import os.path

    from Qt import QtCompat

    # first, inherit the palette of the parent
    if widget.parent():
        widget.setPalette(widget.parent().palette())

    if not uiname:
        uiname = os.path.basename(filename).split('.')[0]

    QtCompat.loadUi(os.path.split(filename)[0] + '/ui/%s.ui' % uiname, widget)
