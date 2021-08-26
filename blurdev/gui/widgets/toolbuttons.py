from __future__ import absolute_import
from Qt.QtGui import QIcon, QMovie
from Qt.QtWidgets import QApplication, QToolButton

# =============================================================================
# CLASSES
# =============================================================================


class AnimatedIconToolButton(QToolButton):
    def __init__(self, filePath, alwaysAnimated=False, *args, **kwargs):
        super(AnimatedIconToolButton, self).__init__(*args, **kwargs)
        self._movie = QMovie(filePath)
        self._alwaysAnimated = alwaysAnimated

    @property
    def alwaysAnimated(self):
        return self._alwaysAnimated

    @property
    def movie(self):
        return self._movie

    def enterEvent(self, event):
        if not self.alwaysAnimated:
            self.movie.setPaused(False)

    def leaveEvent(self, event):
        if not self.alwaysAnimated:
            self.movie.setPaused(True)

    def setPaused(self, state):
        self.movie.setPaused(bool(state))

    def show(self):
        self.movie.start()
        icon = QIcon(self.movie.currentPixmap())
        if not self.alwaysAnimated:
            self.movie.setPaused(True)
        self.setIcon(icon)
        super(AnimatedIconToolButton, self).show()
        while True:
            self.setIcon(QIcon(self.movie.currentPixmap()))
            self.repaint()
            QApplication.processEvents()
