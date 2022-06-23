##
#   \namespace  blurdev.gui
#
#   \remarks    Contains gui components and interfaces
#
#   \author     beta@blur.com
#   \author     Blur Studio
#   \date       06/15/10
#

from __future__ import absolute_import
from Qt.QtCore import Property

from .window import Window  # noqa: F401
from .dialog import Dialog  # noqa: F401
from functools import partial


def QtPropertyInit(name, default, callback=None, typ=None):
    """Initializes a default Property value with a usable getter and setter.

    You can optionally pass a function that will get called any time the property
    is set. If using the same callback for multiple properties, you may want to
    use the blurdev.decorators.singleShot decorator to prevent your function getting
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
    from Qt import QtCompat
    import os.path

    # first, inherit the palette of the parent
    if widget.parent():
        widget.setPalette(widget.parent().palette())

    if not uiname:
        uiname = os.path.basename(filename).split('.')[0]

    QtCompat.loadUi(os.path.split(filename)[0] + '/ui/%s.ui' % uiname, widget)


def connectLogger(
    parent, start=True, sequence='F2', text='Show Logger', objName='uiShowLoggerACT'
):
    """Optionally starts the logger, and creates a QAction on the provided parent with
        the provided keyboard shortcut to run it.

    Args:
        parent: The parent widget, normally a window
        start (bool, optional): Start logging immediately. Defaults to True. Disable if
            you don't want to redirect immediately.
        sequence (str, optional): A string representing the keyboard shortcut associated
            with the QAction. Defaults to 'F2'
        text (str, optional): The display text for the QAction. Defaults to 'Show Logger'
        objName (str, optional): Set the QAction's objectName to this value. Defaults to
            'uiShowLoggerACT'

    Returns:
        QAction: The created QAction
    """
    import blurdev
    from Qt.QtGui import QKeySequence
    from Qt.QtWidgets import QAction

    if start:
        blurdev.core.logger(parent)
    # Create shortcuts for launching the logger
    action = QAction(text, parent)
    action.setObjectName(objName)
    action.triggered.connect(blurdev.core.showLogger)
    action.setShortcut(QKeySequence(sequence))
    parent.addAction(action)
    return action
