##
# 	\namespace	blurdev.ide.addons
#
# 	\remarks	Defines additional addons for the IDE system
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/03/11
#

import sys
import traceback

from blurdev.ide.ideaddon import IdeAddon

_loaded = False

# define global functions
def init():
    global _loaded
    if not _loaded:
        _loaded = True

        import os.path, glob

        filenames = glob.glob(os.path.split(__file__)[0] + '/*/__init__.py')
        for filename in filenames:
            modname = os.path.normpath(filename).split(os.path.sep)[-2]

            # do not import the init module
            if modname != '__init__':
                package = '%s.%s' % (__name__, modname)

                try:
                    __import__(package)
                except:
                    IdeAddon.registerErrored(package, traceback.format_exc())
