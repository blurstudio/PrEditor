""" Defines the different core systems for the blurdev
"""

Core = None

# initialize the system for 3d Studio Max
try:
    from studiomaxcore import StudiomaxCore as Core
except:
    pass

# initialize the system for Softimage
try:
    from softimagecore import SoftimageCore as Core
except:
    pass

# initialize the system for Motion Builder
try:
    from motionbuildercore import MotionBuilderCore as Core
except:
    pass

# import the default core
if not Core:
    from core import Core
