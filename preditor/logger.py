# standard library imports
from __future__ import absolute_import
import json
import logging
import os
import shutil
import sys

# third-party imports
from signalslot import Signal

# blur imports
from .prefs import prefs_path


CORE_MAPPINGS = {
    "fusion": ["fusion"],
    "houdini": ["hmaster", "hython", "houdini", "hescape"],
    "katana": ["katana"],
    "mari": ["mari"],
    "maya": ["maya"],
    "motionbuilder": ["motionbuilder"],
    "nuke": ["nuke"],
    "rv": ["rv"],
    "softimage": ["xsi"],
    "studiomax": ["max"],
}

core_name = ""
logger_config = {}
logger_patched = False
Logger = logging.getLoggerClass()


class LoggerWithSignals(Logger):

    """
    An override of the standard library's `logging.Logger`-class, providing
    signal events for creation of a new logger instance and the change of
    a logger's level.

    Signals:
        level_changed (int): An instance-level signal denoting the level has
            changed for the logger the signal was emitted from. The numeric
            level value is passed-along with the signal as the arg `level`.
        logger_created (LoggerWithSignals): A class-level signal denoting the
            instantiation of a new logger of this class. The newly created
            logger is passed-along with the signal as the arg `logger`.
    """

    # class-level signal
    logger_created = Signal(args=["logger"], name="logger_created")

    # instance-level signal
    level_changed = None

    def __init__(self, name):
        """
        Creates the logger and loads the previous level it was set to based off
        the current core's saved configuration.

        After initialization the `logger_created`-signal is emitted with this
        logger object as its payload.

        Also instantiates the instance-level signal `level_changed`.

        Args:
            name (str): Logger name.
        """
        self.level_changed = Signal(args=["level"], name="level_changed")
        super(LoggerWithSignals, self).__init__(name)

        # restore logger config from core's previous session
        level = getLoggerConfiguration(name)
        if level >= 0:
            self.setLevel(level)

        # emit creation signal
        self.logger_created.emit(logger=self)

    def setLevel(self, level):
        """
        Sets the threshold for this logger to `level`. Also emits the
        instance's `level_changed`-signal with the level number as its payload.

        Args:
            level (int): Numeric level value.
        """
        super(LoggerWithSignals, self).setLevel(level)
        self.level_changed.emit(level=level)


def patchLogger(force=False):
    """
    Replaces the logger class used by `logging` to instantiate new loggers.
    Will also restore the active core's previous logger levels.

    Args:
        force (bool, optional): Force patching of logging logger class when
            True, ignoring whether logging class has already been patched.
            Defaults to False.
    """
    global logger_patched

    if force or not logger_patched:
        # disable logging
        logging._acquireLock()

        try:
            # track patch globally
            logger_patched = True

            # override default logger class with `LoggerWithSignals`
            logging.setLoggerClass(LoggerWithSignals)

        # re-enable logging
        finally:
            logging._releaseLock()

        # restore logger config for loggers initialized pre-patch
        for name, logger in logging.root.manager.loggerDict.items():
            if isinstance(logger, Logger):
                level = getLoggerConfiguration(name)
                if level >= 0:
                    logger.setLevel(level)


def getCoreName(force=False):
    """
    Derives the core name from the currently running executable.

    Args:
        force (bool, optional): Forces derivation of core name, ignoring
            pre-existing calculation of core name. Defaults to False.

    Returns:
        str: Name of core.
    """
    global core_name

    if force or not core_name:

        # use executable name as core name
        if sys.platform == "win32":
            _exe = os.path.basename(sys.executable).replace(".exe", "")

        # the `sys.executable` method on linux does not return the application
        # python may be running in; use process path pid symlink
        else:
            proc_path = os.path.realpath("/proc/{}/exe".format(os.getpid()))
            _exe = os.path.basename(proc_path)

        exe_name = _exe.lower()

        # set core name according to CORE_MAPPINGS dict
        for name, exe_patterns in CORE_MAPPINGS.items():
            if any(pattern in exe_name for pattern in exe_patterns):
                core_name = name
                break

        # use "blurdev" as core name fallback
        if not core_name:
            core_name = "blurdev"

    return core_name


def getLoggerConfiguration(name):
    """
    Retrieves the previous level set for the logger name provided. If no
    previous level configuration is found -1 is returned.

    Args:
        name (str): Name of logger to retrieve level configuration for.

    Returns:
        int: Numeric value representing logger level. Defaults to -1.
    """
    config = loadLoggerConfiguration()
    return config.get(name, -1)


def loadLoggerConfiguration(force=False):
    """
    Retrieves the previously saved logger levels for the current active core.

    Args:
        force (bool, optional): Forces retrieval of logger configuration from
            file. Defaults to False.

    Returns:
        dict: Dictionary of logger levels keyed to they associated logger
            names.
    """
    global logger_config

    if force or not logger_config:
        core_name = getCoreName()
        logger_config_path = prefs_path("loggers.json", core_name=core_name)

        if os.path.exists(logger_config_path):
            try:
                with open(logger_config_path) as logger_config_file_obj:
                    logger_config = json.load(logger_config_file_obj)
            except ValueError:
                logger_config = {}

    return logger_config


def saveLoggerConfiguration():
    """
    Outputs to disk a JSON file of the current core's active loggers' levels.
    """
    # aggregate logger configuration
    logger_config = {"": logging.root.level}
    for name, logger in logging.root.manager.loggerDict.items():
        if not isinstance(logger, logging.PlaceHolder):
            logger_config[name] = logger.level

    # derive config location
    core_name = getCoreName()
    config_path = prefs_path(core_name=core_name)
    logger_config_path = os.path.join(config_path, "loggers.json")
    temp_logger_config_path = logger_config_path + ".temp"

    # ensure destination exists
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    # output logger configuration to temp file then move on success
    try:
        json_str = json.dumps(logger_config, sort_keys=True, indent=4)
        with open(temp_logger_config_path, "w") as logger_config_file_obj:
            logger_config_file_obj.write(json_str)
        shutil.move(temp_logger_config_path, logger_config_path)
    except Exception:
        pass
