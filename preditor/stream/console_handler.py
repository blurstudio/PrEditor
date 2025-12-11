from __future__ import absolute_import

import logging
import re
from dataclasses import dataclass
from typing import Optional

from .. import plugins
from ..constants import StreamType
from . import Manager

logger = logging.getLogger(__name__)


class DefaultDescriptor:
    def __init__(self, *, ident=None, default=None):
        self._default = default
        self._ident = ident

    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type):
        if obj is None:
            return self._default

        return getattr(obj, self._name, self._default)


class LoggingLevelDescriptor(DefaultDescriptor):
    """Converts a string into a logging level or None.

    When set, the string will be converted to an int if possible otherwise the
    provided value is stored.
    """

    _level_conversion = logging.Handler()

    def __set__(self, obj, value):
        if value is None:
            value = logging.NOTSET
        else:
            try:
                value = int(value)
            except ValueError:
                # convert logging level strings to their int values if possible.
                try:
                    self._level_conversion.setLevel(value)
                    value = self._level_conversion.level
                except Exception:
                    logger.warning(f"Unable to convert {value} to an int logging level")
                    value = 0
        setattr(obj, self._name, value)


class FormatterDescriptor(DefaultDescriptor):
    """Stores a logging.Formatter object.

    If a string is passed it will be cast into a Formatter instance.
    """

    def __init__(self, *, ident=None, default=None):
        if isinstance(default, str):
            default = logging.Formatter(default)
        super().__init__(ident=ident, default=default)

    def __set__(self, obj, value):
        if isinstance(value, str):
            value = logging.Formatter(value)
        setattr(obj, self._name, value)


@dataclass
class HandlerInfo:
    name: str
    level: LoggingLevelDescriptor = LoggingLevelDescriptor()
    plugin: Optional[str] = "Console"
    formatter: FormatterDescriptor = FormatterDescriptor()

    _attr_names = {"plug": "plugin", "fmt": "formatter", "lvl": "level"}

    def __post_init__(self):
        # Clear self.name so you can define omit name to define a root logger
        # For example passing "level=INFO" would set the root logger to info.
        name = self.name
        self.name = ""

        parts = self.__to_parts__(name)
        for i, value in enumerate(parts):
            key, _value = self.__parse_setting__(value, i)
            setattr(self, key, _value)

    @classmethod
    def __to_parts__(cls, value):
        """Returns a list of args and kwargs. Kwargs are 2 item tuples."""
        sp = re.split(r'(\w+(?<!\\)=)', value)
        args = [i for i in sp[0].split(',') if i]
        for i in range(1, len(sp), 2):
            value = sp[i + 1].replace("\\=", "=")
            if value.endswith(","):
                value = value[:-1]
            args.append((sp[i][:-1], value))
        return args

    @classmethod
    def __parse_setting__(cls, value, index):
        """Converts a value into its name and value.

        Examples:
            ("preditor", 0) returns ("name", "preditor")
            ("lvl=DEBUG", 0) returns ("level", "INFO")
        """
        if isinstance(value, tuple):
            # The string specified the key so expand it to the property name.
            attr_name = cls._attr_names.get(value[0], value[0])
            value = value[1]
        else:
            # If there is no key defined, map the index to the property name
            i = list(cls.__dataclass_fields__)[index]
            field = cls.__dataclass_fields__[i]
            attr_name = field.name

        return attr_name, value

    def install(self, callback=None, replay=False, disable_writes=False, clear=False):
        """Add the required logging handler if needed and connect callback to it."""
        _logger = logging.getLogger(self.name)
        handler, _ = plugins.add_logging_handler(_logger, self.plugin)
        if handler and callback:
            handler.manager.add_callback(
                callback, replay=replay, disable_writes=disable_writes, clear=clear
            )
        return handler

    def uninstall(self, callback):
        """Remove the callback added via install, doesn't remove the logging handler."""
        _logger = logging.getLogger(self.name)
        handler, _ = plugins.add_logging_handler(_logger, self.plugin)
        if handler:
            handler.manager.remove_callback(callback)


class ConsoleHandler(logging.Handler):
    """A logging handler that writes directly to the PrEditor instance.

    Args:
        formatter (str or logging.Formatter, optional): If specified,
            this is passed to setFormatter.
        stream (optional): If provided write to this stream instead of the
            main preditor instance's console.
        stream_type (StreamType, optional): If not None, pass this value to the
            write call's force kwarg.
    """

    def __init__(self):
        super().__init__()
        self.manager = Manager()

    def emit(self, record):
        try:
            # If no gui has been created yet, or the `preditor.instance()` was
            # closed and garbage collected, there is nothing to do, simply exit
            # msg = self.format(record)
            # self.manager.write(f'{msg}\n', StreamType.CONSOLE)
            self.manager.write((self, record), StreamType.CONSOLE)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
