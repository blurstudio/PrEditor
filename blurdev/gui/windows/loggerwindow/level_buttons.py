import blurdev
import logging
import abc

from blurdev.debug import DebugLevel
from cute.abcmeta import QABCMeta
from Qt.QtCore import QSignalMapper, Signal, QObject
from Qt.QtWidgets import QAction, QToolButton
from blurdev.gui import iconFactory
from collections import OrderedDict
from future.utils import with_metaclass


class LevelButton(with_metaclass(QABCMeta, QToolButton)):
    """A drop down button to set levels.

    Attributes:
        _icon (TYPE): The icon name to use for the button.
        _toolTip (TYPE): The tool tip label. Current level will be appended.
        _levels (TYPE): A dictionary mapping a level to text and color.
            For example: OrderedDict([('HIGH', dict(text='High', color='#808080'))])
    """

    level_changed = Signal(object)

    _icon = 'dot'  # The button icon.
    _levels = OrderedDict([])
    _toolTip = 'Level'  # The text in the tool tip.

    def __init__(self, parent=None, level=None):
        """ Provides a easy way for users to choose a level.

        Args:
            parent (QWidget, optional): The parent widget for this button.
            level (str):
                Set to the desired level.
                If None then use the current level.

        Signals:
            level_changed(object): This signal is emitted when setLevel is called.
        """
        super(QToolButton, self).__init__(parent=parent)
        self.setPopupMode(QToolButton.InstantPopup)
        self._logger = logging.getLogger()
        self._signalMapper = QSignalMapper(self)
        self._signalMapper.mapped[str].connect(self.setLevel)

        for l in self._levels:
            icon = self._getIcon('dot', self._levels[l]['color'])
            action = QAction(icon, self._levels[l]['text'], self)
            action.setCheckable(True)
            self.addAction(action)
            self._signalMapper.setMapping(action, l)
            action.triggered.connect(self._signalMapper.map)

        if level:
            self.setLevel(level)
        else:
            self.refresh()

    def setToolTip(self, level):
        toolTip = '{} ({})'.format(self._toolTip, self._levels[level]['text'])
        super(QToolButton, self).setToolTip(toolTip)

    def refresh(self):
        level = self.level()
        self.setToolTip(level)
        for action in self.actions():
            action.setChecked(action.text() == self._levels[level]['text'])
        self.setIcon(level)

    @abc.abstractmethod
    def level(self):
        """Returns the current level name.

        Returns:
            str: The current level name.
        """
        return ''

    def setIcon(self, level):
        """Set's the icon of the button.

        Args:
            level (str): The level to set the button to.
        """
        icon = self._getIcon(self._icon, self._levels[level]['color'])
        super(QToolButton, self).setIcon(icon)

    @abc.abstractmethod
    def setLevel(self, level):
        """ Sets the logging level.

        Calling this function will emit the level_changed signal.

        Args:
            level (str): The desired debug level.
        """
        self.refresh()
        self.level_changed.emit(level)

    def _getIcon(self, name, color):
        path = iconFactory.getIconPath(name)
        icf = iconFactory.customize(
            iconClass='StyledIcon',
            baseColor=color,
            baseContrast=0,
            activeColor=color,
            activeContrast=0,
            toggleColor=color,
            toggleContrast=0,
            highlightColor=color,
            highlightContrast=0,
        )
        return icf.getIcon(path=path)


class DebugLevelButton(LevelButton):
    _icon = 'bug_report'
    _toolTip = 'Debug Level'
    _levels = OrderedDict(
        [
            ('', dict(text='Disabled', color='#808080')),
            ('Low', dict(text='Low', color='#EEC041')),
            ('Mid', dict(text='Mid', color='#EF8341')),
            ('High', dict(text='High', color='#E74C46')),
        ]
    )

    def level(self):
        return DebugLevel.labelByValue(blurdev.debug.debugLevel())

    def setLevel(self, level):
        blurdev.debug.setDebugLevel(level)
        super(DebugLevelButton, self).setLevel(level)


class LoggingLevelButton(LevelButton):
    _logger = logging.getLogger()
    _icon = 'format_align_left'
    _toolTip = 'Logging Level'
    _levels = OrderedDict(
        [
            ('NOTSET', dict(text='Disabled', color='#808080')),
            ('CRITICAL', dict(text='Critical', color='#E74C46')),
            ('ERROR', dict(text='Error', color='#EF8341')),
            ('WARNING', dict(text='Warning', color='#EEC041')),
            ('INFO', dict(text='Info', color='#038CFC')),
            ('DEBUG', dict(text='Debug', color='#AF45D9')),
        ]
    )

    def level(self):
        return logging.getLevelName(self._logger.level)

    def setLevel(self, level):
        self._logger.setLevel(level)
        super(LoggingLevelButton, self).setLevel(level)
