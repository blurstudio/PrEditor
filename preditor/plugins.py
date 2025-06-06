from __future__ import absolute_import

import logging

from importlib_metadata import EntryPoint, entry_points

_logger = logging.getLogger(__name__)


class Plugins(object):
    def about_module(self):
        plugs = {}
        for ep in self.iterator("preditor.plug.about_module"):
            name = ep.name
            if name in plugs:
                _logger.warning(
                    'Duplicate "preditor.plug.about_module" plugin found with '
                    'name "{}"'.format(name)
                )
            else:
                plugs[name] = ep

        # Sort the plugins alphabetically
        for name in sorted(plugs.keys(), key=lambda i: i.lower()):
            ep = plugs[name]
            try:
                result = ep.load()
            except Exception as error:
                result = "Error processing: {}".format(error)

            yield name, result

    def add_logging_handler(self, logger, handler_cls, *args, **kwargs):
        """Add a logging handler to a logger if not already installed.

        Checks for an existing handler on logger for the specific class(does not
        use isinstance). If not then it will create an instance of the handler
        and add it to the logger.

        Args:
            logger (logging.RootLogger): The logger instance to add the handler.
            handler_cls (logging.Handler or str): If a string is passed it will
                use `self.logging_handlers` to get the class. If not found then
                exits with success marked as False. Other values are treated as
                the handler class to add to the logger.
            *args: Passed to the handler_cls if a new instance is created.
            **kargs: Passed to the handler_cls if a new instance is created.

        Returns:
            logging.Handler or None: The handler instance that was added, already
                has been added, or None if the handler name isn't a valid plugin.
            bool: True only if the handler_cls was not already added to this logger.
        """
        if isinstance(handler_cls, str):
            handlers = dict(self.logging_handlers(handler_cls))
            if not handlers:
                # No handler to add for this name
                return None, False
            handler_cls = handlers[handler_cls]

        # Attempt to find an existing handler instance and return it
        for h in logger.handlers:
            if type(h) is handler_cls:
                return h, False

        # No handler installed create and install it
        handler = handler_cls(*args, **kwargs)
        logger.addHandler(handler)
        return handler, True

    def editor(self, name):
        for plug_name, ep in self.editors(name):
            return plug_name, ep.load()
        return None, None

    def editors(self, name=None):
        for ep in self.iterator(group="preditor.plug.editors"):
            if name and ep.name != name:
                continue
            yield ep.name, ep

    def initialize(self, name=None):
        for ep in self.iterator(group="preditor.plug.initialize"):
            yield ep.load()

    def loggerwindow(self, name=None):
        """Returns instances of "preditor.plug.loggerwindow" plugins.

        These plugins are used by the LoggerWindow to extend its interface. For
        example it can be used to add a toolbar or update the menus.

        When using this plugin, make sure the returned class is a subclass of
        `preditor.gui.logger_window_plugin.LoggerWindowPlugin`.
        """
        for ep in self.iterator(group="preditor.plug.loggerwindow"):
            if name and ep.name != name:
                continue
            yield ep.name, ep.load()

    def logging_handlers(self, name=None):
        for ep in self.iterator(group="preditor.plug.logging_handlers"):
            yield ep.name, ep.load()

    @classmethod
    def iterator(cls, group=None, name=None):
        """Iterates over the requested entry point yielding results."""
        for ep in entry_points().select(group=group):
            yield ep

    @classmethod
    def from_string(cls, value, name="", group=""):
        """Resolve an EntryPoint string into its object.

        Example:
            cls = from_string("preditor.gui.errordialog:ErrorDialog")
        """
        ep = EntryPoint(name=name, value=value, group=group)
        return ep.load()
