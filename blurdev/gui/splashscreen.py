import os
import glob
import random

from PyQt4.QtGui import QPixmap, QSplashScreen
from PyQt4.QtCore import Qt

# Temporary workaround for providing default environment variable for splashscreen source dir.
import platform

if platform.uname()[0] in [
    'Linux',
]:
    SPLASH_ROOT_DEFAULT = '/mnt/dev/dev/share_all/splash'
else:
    SPLASH_ROOT_DEFAULT = r'\\source\source\dev\share_all\splash'


SPLASH_DIR = os.environ.get('BDEV_SPLASHSCREEN_SOURCE_DIR', SPLASH_ROOT_DEFAULT)


def randomSplashScreen(toolname='default', minsize=128):
    splash_dir = os.path.join(SPLASH_DIR, toolname)
    # Fallback to the default splashscreens if the requested toolname folder does not exist
    if not os.path.exists(splash_dir):
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
