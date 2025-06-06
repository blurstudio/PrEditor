from __future__ import absolute_import

__all__ = ["delayables", "FindState", "Qsci", "QsciScintilla"]

import Qt

if Qt.IsPyQt6:
    from PyQt6 import Qsci
    from PyQt6.Qsci import QsciScintilla
elif Qt.IsPyQt5:
    from PyQt5 import Qsci
    from PyQt5.Qsci import QsciScintilla
elif Qt.IsPyQt4:
    from PyQt4 import Qsci
    from PyQt4.Qsci import QsciScintilla
else:
    raise ImportError(
        "QScintilla library is not supported by {}".format(Qt.__binding__)
    )


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


from . import delayables  # noqa: E402
