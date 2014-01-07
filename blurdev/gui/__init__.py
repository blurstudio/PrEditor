##
# 	\namespace	blurdev.gui
#
# 	\remarks	Contains gui components and interfaces
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/15/10
#

import os
import glob
import random

from PyQt4.QtGui import QPixmap, QSplashScreen

from window import Window
from dialog import Dialog
from wizard import Wizard


SPLASH_DIR = r'\\source\source\dev\share_all\splash'


def randomSplashScreen(toolname='default'):
    splash_dir = os.path.join(SPLASH_DIR, toolname)

    if os.path.isdir(splash_dir):
        splash_filepaths = glob.glob(os.path.join(splash_dir, '*.*'))
        if splash_filepaths:
            pixmap = QPixmap(random.choice(splash_filepaths))
            splash = QSplashScreen(pixmap)
            splash.show()
            return splash

    return None


def compPixmap(imageData):
    """
    Composits the given pixmaps or image paths into a single pixmap. It takes a list of lists containing a image path or a pixmap and
    optionaly a list of cordinate data. The cordinate data can be just position [5, 5] or position and size [5, 5, 10, 10]. The first
    item in the list becomes the base canvas being drawn on and ignores the cordinate data.

    Example of two step compositing::
    data = [[trax.gui.findIconFile(r'employeeReview\1')],
            [trax.gui.findIconFile(r'employeeReview\alert'), [5, 5]]]
    map = buildPixmap(data)
    data = [[trax.gui.findIconFile(r'employeeReview\blank')], 
            [map, [4,2]]]
    map = buildPixmap(data)
    """
    from PyQt4.QtGui import QPainter, QPixmap

    if isinstance(imageData[0][0], QPixmap):
        map = imageData[0][0]
    else:
        map = QPixmap(imageData[0][0])
    imageData.pop(0)
    painter = QPainter()
    painter.begin(map)
    for data in imageData:
        if isinstance(data[0], QPixmap):
            overlay = data[0]
        else:
            overlay = QPixmap(data[0])
        rect = map.rect()
        oRect = overlay.rect()
        rect.setSize(oRect.size())
        if len(data) > 1:
            rect.moveTo(data[1][0], data[1][1])
            if len(data[1]) > 2:
                rect.setWidth(data[1][2])
                rect.setHeight(data[1][3])
        painter.drawPixmap(rect, overlay, oRect)
    painter.end()
    return map


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


def findPixmap(filename, thumbSize=None):
    """
        \remarks	looks up a pixmap based on the inputed filename using the QPixmapCache system.  If the autoLoad
                    parameter is true, then it will automatically load the pixmap and return it
        \param		filename	<str>
        \param		thumbSize	<QSize>		size to scale the item to if desired (will affect the search key)
    """
    from PyQt4.QtCore import Qt
    from PyQt4.QtGui import QPixmapCache, QPixmap

    # create the thumbnail size
    if thumbSize:
        w = thumbSize.width()
        h = thumbSize.height()

        ratio = '_%sx%s' % (w, h)

        thumb = QPixmap()

        # load the existing cached thumb file
        if not QPixmapCache.find(filename + ratio, thumb):
            cache = QPixmap()

            # load the existing cached main file
            if not QPixmapCache.find(filename, cache):
                cache.load(filename)

                # cache the source
                QPixmapCache.insert(filename, cache)

            if thumbSize.width() < cache.width() or thumbSize.height() < cache.height():
                thumb = cache.scaled(thumbSize, Qt.KeepAspectRatio)
            else:
                thumb = QPixmap(cache)

            QPixmapCache.insert(filename + ratio, thumb)

        return thumb

    else:
        # try to load the pixmap
        cache = QPixmap()

        # pull the pixmap, autoloading it when necessary
        if not QPixmapCache.find(filename, cache):
            cache.load(filename)

            # cache the source
            QPixmapCache.insert(filename, cache)

        return QPixmap(cache)


def connectLogger(
    parent, start=True, sequence='F2', text='Show Logger', objName='uiShowLoggerACT'
):
    """ Optionally starts the logger, and creates a QAction on the provided parent with the provided
    keyboard shortcut to run it.
    :param parent: The parent widget, normally a window
    :param start: Start logging imeadeately. Defaults to True. Disable if you don't want to redirect imeadeately.
    :param sequence: A string representing the keyboard shortcut associated with the QAction. Defaults to 'F2'
    :param text: The display text for the QAction. Defaults to 'Show Logger'
    :param objName: Set the QAction's objectName to this value. Defaults to 'uiShowLoggerACT'
    :return : The created QAction
    """
    import blurdev
    from PyQt4.QtGui import QAction, QKeySequence

    if start:
        blurdev.core.logger(parent)
    # Create shortcuts for launching the logger
    action = QAction(text, parent)
    action.setObjectName(objName)
    action.triggered.connect(blurdev.core.showLogger)
    action.setShortcut(QKeySequence(sequence))
    parent.addAction(action)
    return action
