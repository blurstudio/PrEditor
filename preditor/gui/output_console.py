from ..utils.cute import QtPropertyInit
from .console_base import ConsoleBase


class OutputConsole(ConsoleBase):
    """A text widget used to show stdout/stderr writes."""

    # Enable these settings by default
    use_console_stylesheet = QtPropertyInit(
        "_use_console_stylesheet", True, callback=ConsoleBase.init_stylesheet
    )
