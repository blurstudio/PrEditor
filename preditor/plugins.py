from __future__ import absolute_import

import six

if six.PY3:
    from importlib_metadata import entry_points
else:
    import pkg_resources


class Plugins(object):
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

    def logging_handlers(self, name=None):
        for ep in self.iterator(group="preditor.plug.logging_handlers"):
            yield ep.name, ep.load()

    @classmethod
    def iterator(cls, group=None, name=None):
        """Iterates over the requested entry point yielding results."""
        if six.PY3:
            for ep in entry_points().select(group=group):
                yield ep
        else:
            for ep in pkg_resources.iter_entry_points(group, name=name):
                yield ep
