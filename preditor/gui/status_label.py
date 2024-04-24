from __future__ import absolute_import

from collections import deque

from Qt.QtCore import QPoint, QTimer
from Qt.QtWidgets import QInputDialog, QLabel, QMenu


class StatusLabel(QLabel):
    """A label that shows text and an average of code execution times in popup menu."""

    def __init__(self, *args, limit=5, **kwargs):
        self.render_as_href = False
        super(StatusLabel, self).__init__(*args, **kwargs)
        self.times = deque(maxlen=limit)

    def clear(self):
        self.setText("")

    def clearTimes(self):
        """"""
        self.times.clear()

    def chooseLimit(self):
        limit, success = QInputDialog.getInt(
            self,
            "Choose Avg length",
            "Choose how many execution time history to keep.",
            value=self.limit(),
            min=1,
            max=100,
        )
        if limit:
            self.setLimit(limit)

    def mouseReleaseEvent(self, event):
        QTimer.singleShot(0, self.showMenu)
        super(StatusLabel, self).mouseReleaseEvent(event)

    def secondsText(self, seconds):
        """Generates text to show seconds of exec time."""
        return 'Exec: {:0.04f} Seconds'.format(seconds)

    def limit(self):
        return self.times.maxlen

    def setLimit(self, limit):
        self.times = deque(self.times, maxlen=limit)

    def setText(self, text):
        if self.render_as_href:
            text = '<a href="showMenu">{}</a>'.format(text)
        super(StatusLabel, self).setText(text)

    def showSeconds(self, seconds):
        self.times.append(seconds)
        self.setText(self.secondsText(seconds))

    def showMenu(self):
        menu = QMenu(self)
        if self.times:
            # Show the time it took to run the last X code calls
            for seconds in self.times:
                menu.addAction(self.secondsText(seconds))

            menu.addSeparator()
            avg = sum(self.times) / len(self.times)
            menu.addAction("Average: {:0.04f}s".format(avg))
            act = menu.addAction("Clear")
            act.triggered.connect(self.clearTimes)

        menu.addSeparator()
        act = menu.addAction("Set limit...")
        act.triggered.connect(self.chooseLimit)

        # Position the menu at the bottom of the widget
        height = self.geometry().height()
        pos = self.mapToGlobal(QPoint(0, height))
        menu.popup(pos)
