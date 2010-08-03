##
# 	\namespace	blurdev.cores.motionbuildercore
#
# 	\remarks	This class is a reimplimentation of the blurdev.cores.core.Core class for running blurdev within Studiomax sessions
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		04/12/10
#

# to be in a 3dsmax session, we need to be able to import the Py3dsMax package
import pyfbsdk
from blurdev.cores.core import Core


# -------------------------------------------------------------------------------------------------------------


class StudiomaxCore(Core):
    def __init__(self):
        Core.__init__(self)
        self.setObjectName('motionbuilder')
