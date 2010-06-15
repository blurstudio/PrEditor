##
# 	\namespace	blurdev.cores
#
# 	\remarks	Defines the different core systems for the blurdev
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

Core = None

# import package specific cores
try:
    from studiomaxcore import StudiomaxCore as Core
except:
    pass

try:
    from softimagecore import SoftimageCore as Core
except:
    pass

# import the default core
if not Core:
    from core import Core
