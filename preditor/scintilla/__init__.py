from __future__ import absolute_import


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


from . import delayables  # noqa: F401, E402
