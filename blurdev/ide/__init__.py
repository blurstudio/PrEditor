##
# 	\namespace	blurdev.ide
#
# 	\remarks	The blurdev IDE allows you to quickly and easily create and edit python files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#


class FindState(object):
    """
    Arguments:
        end_pos (int): The position in the document to stop searching. If None, then
            search to the end of the document.
    """

    def __init__(self):
        self.expr = ''
        self.wrap = True
        self.wrapped = False
        self.forward = True
        self.flags = 0
        self.start_pos = 0
        self.start_pos_original = None
        self.end_pos = None


from .ideeditor import IdeEditor
from .ideproject import IdeProject
from .ideaddon import IdeAddon
from .ideregistry import RegistryType
