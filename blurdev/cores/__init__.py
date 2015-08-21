""" Defines the different core systems for the blurdev
"""

import sys
import os

Core = None

_exe = os.path.basename(sys.executable).lower()

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

if Core is None:
    # import the default core
    from core import Core
