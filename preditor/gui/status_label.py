from __future__ import absolute_import

from collections import deque
from functools import partial

from Qt.QtCore import QPoint, QTimer
from Qt.QtWidgets import QApplication, QInputDialog, QLabel, QMenu


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

    def copy_action_text(self, action):
        """Copy the text of the provided action into the clipboard."""
        QApplication.clipboard().setText(action.text())

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
        self.setText(self.secondsText(seconds[0]))

    def showMenu(self):
        menu = QMenu(self)
        if self.times:
            # Show the time it took to run the last X code calls
            times = []
            for seconds in self.times:
                secs, cmd = seconds
                times.append(secs)

                # Add a simplified copy of the command that was run
                cmd = cmd.strip()
                cmds = cmd.split("\n")
                if len(cmds) > 1 or len(cmds[0]) > 50:
                    cmd = "{} ...".format(cmds[0][:50])
                # Escape &'s so they dont' get turned into a shortcut'
                cmd = cmd.replace("&", "&&")
                act = menu.addAction("{}:  {}".format(self.secondsText(secs), cmd))
                # Selecting this action should copy the time it took to run
                act.triggered.connect(partial(self.copy_action_text, act))

            menu.addSeparator()
            avg = sum(times) / len(times)
            act = menu.addAction("Average: {:0.04f}s".format(avg))
            act.triggered.connect(partial(self.copy_action_text, act))

            act = menu.addAction("Clear")
            act.triggered.connect(self.clearTimes)

        menu.addSeparator()
        act = menu.addAction("Set limit...")
        act.triggered.connect(self.chooseLimit)

        # Position the menu at the bottom of the widget
        height = self.geometry().height()
        pos = self.mapToGlobal(QPoint(0, height))
        menu.popup(pos)
