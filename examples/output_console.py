"""Example of using `preditor.gui.output_console.OutputConsole` in a UI.

`python output_console.py`
"""


import logging
import sys
from argparse import ArgumentParser

import Qt
from Qt.QtCore import QDateTime
from Qt.QtWidgets import QApplication, QMainWindow

import preditor
from preditor.contexts import OverrideConsoleStreams

logger_a = logging.getLogger("logger_a")
logger_a_child = logging.getLogger("logger_a.child")
logger_b = logging.getLogger("logger_b")
logger_c = logging.getLogger("logger_c")

# Define a custom logging level name. This should be discouraged but logging
# supports it so PrEditor should as well.
SUPER_INFO_LEVEL = logging.INFO - 5
logging.addLevelName(SUPER_INFO_LEVEL, "SUPER_INFO")


class ExampleApp(QMainWindow):
    def __init__(self, parent=None, init_preditor=True):
        super().__init__(parent=parent)
        # Use a .ui file to simplify the example code setup.
        Qt.QtCompat.loadUi(__file__.replace(".py", ".ui"), self)

        # Connect signals to test buttons
        self.uiClearBTN.released.connect(self.clear_all)
        self.uiAllLoggingDebugBTN.released.connect(self.all_logging_level_debug)
        self.uiAllLoggingWarningBTN.released.connect(self.all_logging_level_warning)
        self.uiAllLoggingPrintBTN.released.connect(self.all_logging_print)
        self.uiAllLoggingRaiseBTN.released.connect(self.all_logging_raise)
        self.uiAllLoggingChangeHandlersBTN.released.connect(
            self.all_logging_change_handlers
        )
        self.uiUsePrEditorStyleCHK.toggled.connect(self.set_stdout_style)
        self.uiRemovePrEditorStyleBTN.released.connect(self.clear_stdout_style)
        self.uiLoggingCriticalBTN.released.connect(self.level_critical)
        self.uiLoggingErrorBTN.released.connect(self.level_error)
        self.uiLoggingWarningBTN.released.connect(self.level_warning)
        self.uiLoggingInfoBTN.released.connect(self.level_info)
        self.uiLoggingDebugBTN.released.connect(self.level_debug)
        self.uiErrorBTN.released.connect(self.raise_exception)
        self.uiPrintTimeBTN.released.connect(self.print_time)
        self.uiPrintTimeErrBTN.released.connect(self.print_time_stderr)
        self.uiSendLoggingBTN.released.connect(self.send_logging)

        # 1. Create the preditor instance and connect to the console's controllers
        if init_preditor:
            plog = preditor.instance(parent=self, create=True)
            preditor.connect_preditor(self)
            self.uiAllLog.controller = plog
            self.uiSelectLog.controller = plog
            self.uiStdout.controller = plog
            self.uiStderr.controller = plog
        else:
            self.setWindowTitle(f"{self.windowTitle()} - No PrEditor")

        # 2. Configure the various OutputConsole widgets.
        # Note: this can be done in the .ui file, but for this example we will
        # configure it in code.

        # See this method for how to configure uiAllLog to show all logging
        # messages of all levels
        self.all_logging_level_warning()
        # Configure the default logging formatter for this widget.
        self.uiAllLog.logging_formatter_str = (
            "<<%(levelname)s| %(name)s: Line: %(lineno)d>> %(message)s"
        )

        # Configure uiSelectLog to show logging messages from specific handlers
        self.uiSelectLog.logging_handlers = [
            (
                "logger_a,DEBUG,fmt=[%(levelname)s %(module)s.%(funcName)s "
                "line:%(lineno)d] %(message)s"
            ),
            "logger_b,WARNING",
        ]
        # And show tracebacks without showing all stderr text
        self.uiSelectLog.stream_echo_tracebacks = True

        # Configure uiStdout to only show stdout text
        self.uiStdout.stream_echo_stdout = True

        # Configure uiStderr to only show stderr text
        self.uiStderr.stream_echo_stderr = True

    def all_logging_change_handlers(self):
        """Demonstrate temporarily changing logging_handlers for uiAllLog.

        This changes uiAllLog to only show a subset of loggers not all of them.
        It sends the same logging messages as the "Send Logging Message" Button,
        but due to the updated filtering it shows very different results.
        """
        handlers = [
            # Only show logger_a warnings
            "logger_a_child,level=WARNING",
            # And enable showing a custom logging level message. This is normally
            # hidden unless the logging level is set to debug or SUPER_INFO.
            # Note that we can pass SUPER_INFO because of the `addLevelName` call.
            "logger_c,level=SUPER_INFO",
        ]
        with OverrideConsoleStreams(self.uiAllLog, logging_handlers=handlers):
            self.send_logging()

    def all_logging_level_debug(self):
        """Update this widget to show up to debug messages for all loggers.
        Hide the PyQt loggers as they just clutter the output for this demo.
        """
        self.uiAllLog.logging_handlers = [
            "root,level=DEBUG",
            "PyQt5,level=CRITICAL",
            "PyQt6,level=CRITICAL",
            "logger_b,fmt=[%(levelname)s:%(name)s] %(message)s",
        ]

    def all_logging_level_warning(self):
        """Update this widget to show up to warning messages for all loggers.
        Hide the PyQt loggers as they just clutter the output for this demo.
        """
        self.uiAllLog.logging_handlers = [
            "root,level=WARNING",
            # Suppress PyQt logging messages like the .ui file parsing
            # logging messages created when first showing the PrEditor instance.
            "PyQt5,level=CRITICAL",
            "PyQt6,level=CRITICAL",
            # Replace the default logging_formatter_str formatter only for logger_b
            "logger_b,fmt=[%(levelname)s:%(name)s] %(message)s",
        ]

    def all_logging_print(self):
        """Show temporarily enabling showing prints inside multiple consoles."""
        with OverrideConsoleStreams([self.uiAllLog, self.uiSelectLog], stdout=True):
            print("This print is also shown in All logging and Select Logging.")
        print("This print is NOT shown in All logging and Select Logging.")

    def all_logging_raise(self):
        """Show temporarily enabling showing tracebacks in uiAllLog."""
        with OverrideConsoleStreams(self.uiAllLog, tracebacks=True):
            print("This print is NOT shown in All logging.")
            raise RuntimeError("This Exception is also shown in All logging.")

    def clear_all(self):
        """Clear the text from all consoles"""
        self.uiAllLog.clear()
        self.uiSelectLog.clear()
        self.uiStdout.clear()
        self.uiStderr.clear()

    def clear_stdout_style(self):
        """Reset uiStdout's style to not use PrEditor's style."""
        self.uiUsePrEditorStyleCHK.setChecked(False)
        self.uiStdout.setStyleSheet(None)

    def level_critical(self):
        logging.root.setLevel(logging.CRITICAL)

    def level_error(self):
        logging.root.setLevel(logging.ERROR)

    def level_warning(self):
        logging.root.setLevel(logging.WARNING)

    def level_info(self):
        logging.root.setLevel(logging.INFO)

    def level_debug(self):
        logging.root.setLevel(logging.DEBUG)

    def message_time(self):
        return f"The time is: {QDateTime.currentDateTime().toString()}"

    def print_time(self):
        print(self.message_time())

    def print_time_stderr(self):
        print(self.message_time(), file=sys.stderr)

    def raise_exception(self):
        raise RuntimeError(self.message_time())

    def set_stdout_style(self, state):
        """Enable/disable uiStdout using PrEditor's style.

        Note: Disabling it doesn't clear the style, just prevent it from being
        automatically updated when changed in PrEditor.
        """
        self.uiStdout.use_console_stylesheet = state

    def send_logging(self):
        logger_a.critical("A critical msg for logger_a")
        logger_a.error("A error msg for logger_a")
        logger_a.warning("A warning msg for logger_a")
        logger_a.info("A info msg for logger_a")
        logger_a.debug("A debug msg for logger_a")
        logger_a_child.warning("A warning msg for logger_a.child")
        logger_a_child.debug("A debug msg for logger_a.child")
        logger_b.warning("A warning msg for logger_b")
        logger_b.debug("A debug msg for logger_b")
        logger_c.warning("A warning msg for logger_c")
        logger_c.debug("A debug msg for logger_c")
        logger_c.log(
            SUPER_INFO_LEVEL,
            "A custom logging level msg for logger_c that is normally hidden "
            "unless using debug or the custom level.",
        )
        logging.root.warning("A warning msg for logging.root")
        logging.root.debug("A debug msg for logging.root")


if __name__ == '__main__':
    parser = ArgumentParser("Example of using OutputConsole features.")
    parser.add_argument(
        "--no-preditor",
        action="store_true",
        help="Don't init and install the PrEditor console.",
    )
    args = parser.parse_args()

    # Configure PrEditor for this application, start capturing all text output
    # from stderr/stdout so once PrEditor is launched, it can show this text.
    # This does not initialize any QtGui/QtWidgets.
    if not args.no_preditor:
        preditor.configure(
            # This is the name used to store PrEditor preferences and workboxes
            # specific to this application.
            'output_console',
        )

    # Create a Gui Application allowing the user to show PrEditor
    app = QApplication(sys.argv)
    main_gui = ExampleApp(init_preditor=not args.no_preditor)

    main_gui.show()
    app.exec_()
