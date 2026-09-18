from Qt.QtWidgets import QStackedWidget

from .dialog import Dialog  # noqa: F401
from .window import Window  # noqa: F401


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


def tab_widget_for_tab(tab_widget):
    """Returns the `QTabWidget` `tab_widget` is parented to or `None`."""
    tab_parent = tab_widget.parent()
    if not isinstance(tab_parent, QStackedWidget):
        return None
    return tab_parent.parent()
