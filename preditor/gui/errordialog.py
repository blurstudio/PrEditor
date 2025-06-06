from __future__ import absolute_import

import os
import traceback

from Qt.QtCore import Qt
from Qt.QtGui import QColor, QPixmap

from .. import __file__ as pfile
from . import Dialog, QtPropertyInit, loadUi


class ErrorDialog(Dialog):
    # These Qt Properties can be customized using style sheets.
    errorMessageColor = QtPropertyInit('_errorMessageColor', QColor(Qt.GlobalColor.red))

    def __init__(self, parent):
        super(ErrorDialog, self).__init__(parent)

        loadUi(__file__, self)

        self.parent_ = parent
        self.setWindowTitle('Error Occurred')
        self.uiErrorLBL.setTextFormat(Qt.RichText)
        self.uiIconLBL.setPixmap(
            QPixmap(
                os.path.join(
                    os.path.dirname(pfile),
                    'resource',
                    'img',
                    'warning-big.png',
                )
            ).scaledToHeight(64, Qt.SmoothTransformation)
        )

        self.uiLoggerBTN.clicked.connect(self.show_logger)
        self.uiIgnoreBTN.clicked.connect(self.close)

    def setText(self, exc_info):
        self.traceback_msg = "".join(traceback.format_exception(*exc_info))
        msg = (
            'The following error has occurred:<br>'
            '<br><font color=%(color)s>%(text)s</font>'
        )
        self.uiErrorLBL.setText(
            msg
            % {
                'text': self.traceback_msg.split('\n')[-2],
                'color': self.errorMessageColor.name(),
            }
        )

    def show_logger(self):
        """Create/show the main PrEditor instance with the full traceback."""
        from .. import launch

        launch()
        self.close()

    @classmethod
    def show_prompt(cls, *exc_info):
        """Return False to this dialog should not be shown on an exception.

        This is useful for applications like Nuke which uses exceptions to signal
        traditionally non-exception worthy events, such as when a user cancels
        an Open File dialog window.
        """
        return True
