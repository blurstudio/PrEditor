from __future__ import absolute_import

__all__ = ["ensureWindowIsVisible"]
from Qt.QtWidgets import QApplication


def ensureWindowIsVisible(widget):
    """
    Checks the widget's geometry against all of the system's screens. If it does
    not intersect, it will reposition it to the top left corner of the highest
    numbered screen. Returns a boolean indicating if it had to move the widget.
    """
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
