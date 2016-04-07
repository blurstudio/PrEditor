import os
import glob
import random

from PyQt4.QtGui import QPixmap, QSplashScreen
from PyQt4.QtCore import Qt

SPLASH_DIR = os.environ.get('BDEV_SPLASHSCREEN_SOURCE_DIR')


def randomSplashScreen(toolname='default', minsize=128, allowDefault=True):
    """ Randomly picks a image for the provided toolname and returns a QSplashScreen or None.
    
    The QSplashScreen will have show() called on it when it is returned.
    
    Args:
        toolname (str): The name of a sub-directory of the directory defined in 
            BDEV_SPLASHSCREEN_SOURCE_DIR. If this directory does not exist, it will 
            use the default directory. Defaults to 'default'.
        minsize (int): If the randomly picked image is smaller than minsize, it will
            be scaled up to this size using Qt.KeepAspectRatio. Defaults to 128.
        allowDefault (bool): If False is passed do not fallback to the 'default'
            directory. Defaults to True
    
    Returns:
        QSplashScreen: If a image was picked a QSplashScreen will be returned. Otherwise
            None will be returned.
    """
    splash_dir = os.path.join(SPLASH_DIR, toolname)
    # Fallback to the default splashscreens if the requested toolname folder does not exist
    if allowDefault and not os.path.exists(splash_dir):
        splash_dir = os.path.join(SPLASH_DIR, 'default')

    if os.path.isdir(splash_dir):
        splash_filepaths = glob.glob(os.path.join(splash_dir, '*.*'))
        if splash_filepaths:
            pixmap = QPixmap(random.choice(splash_filepaths))
            if minsize and pixmap.width() < minsize and pixmap.height() < minsize:
                pixmap = pixmap.scaled(
                    minsize, minsize, aspectRatioMode=Qt.KeepAspectRatio
                )
            splash = QSplashScreen(pixmap)
            splash.show()
            return splash

    return None
