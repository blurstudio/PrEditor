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

from PyQt4.QtCore import pyqtProperty
from PyQt4.QtGui import QPixmap, QSplashScreen

from window import Window
from dialog import Dialog
from dockwidget import DockWidget
from wizard import Wizard
from functools import partial


SPLASH_DIR = r'\\source\source\dev\share_all\splash'


def pyqtPropertyInit(name, default, callback=None):
    """Initializes a default pyqtProperty value with a usable getter and setter.
    
    You can optionally pass a function that will get called any time the property
    is set. If using the same callback for multiple properties, you may want to 
    use the blurdev.decorators.singleShot decorator to prevent your function getting
    called multiple times at once. This callback must accept the attribute name and
    value being set.

    Example:
        class TestClass(QWidget):
            def __init__(self, *args, **kwargs):
                super(TestClass, self).__init__(*args, **kwargs)

            stdoutColor = pyqtPropertyInit('_stdoutColor', QColor(0, 0, 255))
            pyForegroundColor = pyqtPropertyInit('_pyForegroundColor', QColor(0, 0, 255))

    Args:
        name(str): The name of internal attribute to store to and lookup from.
        default: The property's default value.  This will also define the pyqtProperty type.
        callback(callable): If provided this function is called when the property is set.

    Returns:
        pyqtProperty
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
    return pyqtProperty(
        default.__class__, fget=(lambda s: ga(s, name)), fset=(lambda s, v: sa(s, v)),
    )


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


def readCSS(path, translateUrls=True, cwd=None):
    """Loads a CSS file from the path specified, and optionally translates paths
    and replaces relative paths.

    Args:
        path (str): Path to the CSS file to read.
        translateUrls (bool, optional): If True, URLs in the CSS file will be
            translated for the current OS using trax.api.data.Mapping.translatePath().
            Defaults to True.
        cwd (None, optional): If specified, relative paths in the CSS file will
            be made absolute with cwd as the base directory.  Otherwise relative
            paths will be left untouched.  Defaults to None.

    Returns:
        str: The contents of the CSS file after the requested path modifications
            have been performed.
    """
    if translateUrls:
        try:
            from trax.api.data import Mapping
        except ImportError:
            translateUrls = False
    import re

    if not os.path.isfile(path):
        raise IOError('Specified CSS file ({}) not found.'.format(path))
    with open(path) as f:
        css = f.read()

    if cwd:
        if translateUrls:
            # if cwd is specified and we're translating paths, translate it
            cwd = Mapping.translatePath(cwd)
        if not os.path.exists(cwd):
            # if cwd does not exist, we will ignore it.
            cwd = None
    if translateUrls or cwd:
        # if translation or custom CWD are enabled, we'll substitute accordingly
        def _replace(match, translate=translateUrls, cwd=cwd):
            ret = r'url({})'
            url = match.group(1)
            if translate or cwd:
                if url.startswith(':/'):
                    # it's a resource path.  Do nothing.
                    pass
                elif re.match(r'^(?:[a-zA-Z]:(?:\\|/)|/).*', url):
                    # it's an absolute path.  Translate it.
                    if translate:
                        url = Mapping.translatePath(url)
                else:
                    # it should be a relative path.
                    if translate:
                        # if path translation is enabled, translate the path
                        # (this should really just be switching slash dir
                        # like os.path.normpath at this point, but we'll call
                        # translatePath in case it needs to do more in the future.)
                        url = Mapping.translatePath(url)
                    if cwd:
                        # if we have a custom cwd, join it now.
                        url = os.path.join(cwd, url)
                # Qt don't play with no backslashes.
                url = url.replace('\\', '/')
            return ret.format(url)

        # iterate over url matches with our replacement function.
        css = re.sub(r'url\((.+?)\)', _replace, css)
    return css


def compPixmap(imageData):
    """
    Composites the given pixmaps or image paths into a single pixmap. It takes a list of lists containing a image path or a pixmap and
    optionaly a list of cordinate data. The cordinate data can be just position [5, 5] or position and size [5, 5, 10, 10]. The first
    item in the list becomes the base canvas being drawn on and ignores the cordinate data.

    Example of two step compositing::
    data = [[trax.gui.findIconFile(r'employeeReview\1')],
            [trax.gui.findIconFile(r'employeeReview\alert'), [5, 5]]]
    map = compPixmap(data)
    data = [[trax.gui.findIconFile(r'employeeReview\blank')], 
            [map, [4,2]]]
    map = compPixmap(data)
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
    :param start: Start logging immediately. Defaults to True. Disable if you don't want to redirect immediately.
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
