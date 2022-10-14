from __future__ import absolute_import

import pkg_resources


class Plugins(object):
    def initialize(self, name=None):
        handlers = pkg_resources.iter_entry_points(
            "preditor.plug.initialize", name=name
        )
        for handler in handlers:
            yield handler.load()

    def logging_handlers(self, name=None):
        handlers = pkg_resources.iter_entry_points(
            "preditor.plug.logging_handlers", name=name
        )
        for handler in handlers:
            yield handler.name, handler.load()
