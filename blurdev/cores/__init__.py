""" Defines the different core systems for the blurdev
"""

import sys
import os

Core = None

if sys.platform == 'win32':
    _exe = os.path.basename(sys.executable).lower()
else:
    # On linux sys.executable does not return the application that python is embedded inside
    _exe = os.path.basename(os.path.realpath('/proc/{}/exe'.format(os.getpid())))

# initialize the system for Motion Builder
if 'maya' in _exe:
    try:
        from mayacore import MayaCore as Core
    except:
        pass

# initialize the system for Motion Builder
if 'motionbuilder' in _exe:
    try:
        from motionbuildercore import MotionBuilderCore as Core
    except:
        pass

# initialize the system for 3d Studio Max
elif 'max' in _exe:
    try:
        from studiomaxcore import StudiomaxCore as Core
    except:
        pass

# initialize the system for Softimage
elif 'xsi' in _exe:
    try:
        from softimagecore import SoftimageCore as Core
    except:
        pass

# initialize the system for running inside Fusion
elif 'fusion' in _exe:
    try:
        from fusioncore import FusionCore as Core
    except:
        pass

# initialize the system for running inside Nuke
elif 'nuke' in _exe:
    from nukecore import NukeCore as Core

    try:
        from nukecore import NukeCore as Core
    except:
        pass

# initialize the system for running inside RV
elif 'rv' in _exe:
    from rvcore import RVCore as Core

    try:
        from rvcore import RVCore as Core
    except:
        pass

if Core is None:
    # import the default core
    from core import Core
