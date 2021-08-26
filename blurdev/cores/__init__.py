""" Defines the different core systems for the blurdev
"""

from __future__ import absolute_import
import sys
import os

Core = None

if sys.platform == 'win32':
    _exe = os.path.basename(sys.executable).lower()
else:
    # On linux sys.executable does not return the application that python is embedded
    # inside
    _exe = os.path.basename(
        os.path.realpath('/proc/{}/exe'.format(os.getpid()))
    ).lower()

# Houdini uses many different executables, so we'll make a list to check against
_houdiniExecs = ['hmaster', 'hython', 'houdini', 'hescape']

# initialize the system for Motion Builder
if 'maya' in _exe:
    try:
        from .mayacore import MayaCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for Motion Builder
if 'motionbuilder' in _exe:
    try:
        from .motionbuildercore import MotionBuilderCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for 3d Studio Max
elif 'max' in _exe:
    try:
        from .studiomaxcore import StudiomaxCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for Softimage
elif 'xsi' in _exe:
    try:
        from .softimagecore import SoftimageCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for running inside Fusion
elif 'fusion' in _exe:
    try:
        from .fusioncore import FusionCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for running inside Nuke
elif 'nuke' in _exe:
    try:
        from .nukecore import NukeCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for running inside Mari
elif 'mari' in _exe:
    from .maricore import MariCore as Core  # noqa: F811

    try:
        from .maricore import MariCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for running inside Houdini
elif any(exeName in _exe for exeName in _houdiniExecs):
    try:
        from .houdinicore import HoudiniCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for running inside RV
elif 'rv' in _exe:
    from .rvcore import RVCore as Core  # noqa: F811

    try:
        from .rvcore import RVCore as Core  # noqa: F811
    except Exception:
        pass

# initialize the system for Softimage
elif 'katana' in _exe:
    try:
        from .katanacore import KatanaCore as Core  # noqa: F811
    except Exception:
        pass

if Core is None:
    # import the default core
    from .core import Core
