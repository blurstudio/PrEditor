from __future__ import absolute_import

__all__ = ["ensureWindowIsVisible"]
from Qt.QtWidgets import QApplication


def ensureWindowIsVisible(widget):
    """
    Checks the widget's geometry against all of the system's screens. If it does
    not intersect it will reposition it to the top left corner of the highest
    numbered desktop.  Returns a boolean indicating if it had to move the
    widget.
    """
    desktop = QApplication.desktop()
    geo = widget.geometry()
    for screen in range(desktop.screenCount()):
        monGeo = desktop.screenGeometry(screen)
        if monGeo.intersects(geo):
            break
    else:
        geo.moveTo(monGeo.x() + 7, monGeo.y() + 30)
        # setting the geometry may trigger a second check if setGeometry is overridden
        disable = hasattr(widget, 'checkScreenGeo') and widget.checkScreenGeo
        if disable:
            widget.checkScreenGeo = False
        widget.setGeometry(geo)
        if disable:
            widget.checkScreenGeo = True
        return True
    return False
