##
# 	\namespace	blurdev.gui
#
# 	\remarks	Contains gui components and interfaces
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/15/10
#

from window import Window
from dialog import Dialog


def loadUi(filename, widget, uiname=''):
    """
        \remarks	use's Qt's uic loader to load dynamic interafces onto the inputed widget
        \param		filename	<str>
        \param		widget		<QWidget>
    """
    import PyQt4.uic
    import os.path

    # first, inherit the palette of the parent
    if widget.parent():
        widget.setPalette(widget.parent().palette())

    if not uiname:
        uiname = os.path.basename(filename).split('.')[0]

    PyQt4.uic.loadUi(os.path.split(filename)[0] + '/ui/%s.ui' % uiname, widget)
