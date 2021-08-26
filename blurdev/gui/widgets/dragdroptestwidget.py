##
# 	:namespace	blurdev.gui.widgets
#
# 	:remarks	Contains classes for generic widget controls
#
# 	:author		beta@blur.com
# 	:author		Blur Studio
# 	:date		07/09/10
#

from __future__ import unicode_literals
from __future__ import absolute_import
from Qt.QtGui import QDropEvent
from Qt.QtWidgets import QTextEdit
from Qt.QtCore import QMimeData, Qt
import cgi


class DragDropTestWidget(QTextEdit):
    def __init__(self, parent=None):
        super(DragDropTestWidget, self).__init__(parent)
        self.excludeFormats = set(
            [
                'text/plain',
                'text/uri-list',
                'text/html',
                'text/uri-lis',
                'application/x-color',
            ]
        )
        # a cached instance of the last drop QMimeData
        # Note: this object can be deleted by the time you get access to it.
        self.lastMime = None

    def insertFromMimeData(self, mimeData):
        self.logEvent(mimeData)

    def logEvent(self, event):
        html = []
        if isinstance(event, QDropEvent):
            html.append(
                '<h1>Drop Event</h1><small><b>source:</b></small> %s'
                % cgi.escape(str(event.source()))
            )
            html.append(
                '<small><b>proposed action:</b></small> %s'
                % cgi.escape(str(event.proposedAction()))
            )
            possibleActions = event.possibleActions().__int__()
            html.append('<small><b>possible actions:</b></small> %i' % possibleActions)
            actions = {
                Qt.CopyAction: 'Copy',
                Qt.MoveAction: 'Move',
                Qt.LinkAction: 'Link',
                Qt.ActionMask: 'action Mask',
                Qt.IgnoreAction: 'ignore',
                Qt.TargetMoveAction: 'target move action',
            }
            for key in sorted(actions.keys()):
                if possibleActions & key and key <= possibleActions:
                    html.append(
                        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<small><b>%s</b></small> %i'
                        % (cgi.escape(actions[key]), key)
                    )
            data = event.mimeData()
        elif isinstance(event, QMimeData):
            html.append('<h1>insertFromMimeData Event</h1><small><b></b></small>')
            data = event
        # Mime Data
        self.lastMime = data
        html.append(
            '<hr><h1>Mime Data</h1><small><b>has color:</b></small> %r'
            % data.hasColor()
        )
        html.append('<small><b>has html:</b></small> %r' % data.hasHtml())
        html.append('<small><b>has image:</b></small> %r' % data.hasImage())
        html.append('<small><b>has text:</b></small> %r' % data.hasText())
        html.append('<small><b>has urls:</b></small> %r' % data.hasUrls())
        html.append('<br>')
        html.append('<small><b>text:</b></small> %s' % cgi.escape(data.text()))
        html.append('<small><b>html:</b></small> %s' % cgi.escape(data.html()))
        html.append(
            '<small><b>urls:</b></small><br> %s'
            % '<br>'.join([cgi.escape(url.toString()) for url in data.urls()])
        )
        html.append('<small><b>Additional Formats:</b></small>')
        for f in data.formats():
            if f not in self.excludeFormats:
                try:
                    html.append(
                        '&nbsp;&nbsp;&nbsp;&nbsp;<small><b>%s: </b></small>%s'
                        % (cgi.escape(f), cgi.escape(data.data(f)))
                    )
                except UnicodeDecodeError:
                    html.append(
                        (
                            '&nbsp;&nbsp;&nbsp;&nbsp;<small><b>%s: '
                            '</b></small><b>UnicodeDecodeError</b>'
                        ) % cgi.escape(f)
                    )

        self.setText('<br>'.join(html))

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        self.logEvent(event)

    @staticmethod
    def runTest():
        from blurdev.gui import Dialog
        from Qt.QtWidgets import QVBoxLayout

        dlg = Dialog()
        dlg.setWindowTitle('Drag Drop Test')

        widget = DragDropTestWidget(dlg)

        layout = QVBoxLayout()
        layout.addWidget(widget)
        dlg.setLayout(layout)

        dlg.show()
        return dlg
