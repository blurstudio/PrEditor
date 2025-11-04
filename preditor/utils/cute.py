__all__ = ["ensureWindowIsVisible"]
from functools import partial

# NOTE: Only import QtWidgets and QtGui inside functions not at the module level
# to preserve headless environment support.
from Qt.QtCore import Property


def ensureWindowIsVisible(widget):
    """
    Checks the widget's geometry against all of the system's screens. If it does
    not intersect, it will reposition it to the top left corner of the highest
    numbered screen. Returns a boolean indicating if it had to move the widget.
    """
    from Qt.QtWidgets import QApplication

    screens = QApplication.screens()
    geo = widget.geometry()

    for screen in screens:
        if screen.geometry().intersects(geo):
            break
    else:
        monGeo = screens[-1].geometry()  # Use the last screen available
        geo.moveTo(monGeo.x() + 7, monGeo.y() + 30)

        # Setting the geometry may trigger a second check if setGeometry is overridden
        disable = hasattr(widget, 'checkScreenGeo') and widget.checkScreenGeo
        if disable:
            widget.checkScreenGeo = False
        widget.setGeometry(geo)
        if disable:
            widget.checkScreenGeo = True
        return True
    return False


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
            if typ is not set. To define a property containing a list, dict or set,
            pass the list, dict, or set class not an instance of the class. Ie pass
            `list` not `[]`. See flake8-bugbear rule B006 for more info.
        callback(callable): If provided this function is called when the property is
            set.
        typ (class, optional): If not None this value is used to specify the type of
            the Property. This is useful when you need to specify a property as python's
            object but pass a default value of a given class.

    Returns:
        Property
    """

    # Prevent all instances of class sharing a mutable data structure. If the
    # default is one of these classes and not a instance of them, replace them
    # with an instance of the default class.
    # See flake8-bugbear B006: Do not use mutable data structures for argument
    # defaults. They are created during function definition time. All calls to
    # the function reuse this one instance of that data structure, persisting
    # changes between them.
    is_mutable = default in (list, dict, set)

    def _getattrDefault(default, is_mutable, self, attrName):
        try:
            value = getattr(self, attrName)
        except AttributeError:
            # Create a unique instance of the default mutable class for self.
            if is_mutable:
                default = default()

            setattr(self, attrName, default)
            return default
        return value

    def _setattrCallback(callback, attrName, self, value):
        setattr(self, attrName, value)
        if callback:
            callback(self, attrName, value)

    ga = partial(_getattrDefault, default, is_mutable)
    sa = partial(_setattrCallback, callback, name)
    # Use the default value's class if typ is not provided.
    if typ is None:
        if is_mutable:
            # In this case the type is the same as the default
            typ = default
        else:
            typ = default.__class__
    return Property(typ, fget=(lambda s: ga(s, name)), fset=(lambda s, v: sa(s, v)))
