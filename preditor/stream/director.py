from __future__ import absolute_import, print_function

import io
import sys

from . import STDERR, STDOUT


class Director(io.TextIOBase):
    """A file like object that stores the text written to it in a manager.
    This manager can be shared between multiple Directors to build a single
    continuous history of all writes.

    Args:
        manager (Manager): The manager that writes are stored in.
        state: The state passed to the manager. This is often ``preditor.stream.STDOUT``
            or ``preditor.stream.STDERR``.
        old_stream: A second stream that will be written to every time this stream
            is written to. This allows this object to replace sys.stdout and still
            send that output to the original stdout, which is useful for not breaking
            DCC's script editors. Pass False to disable this feature. If you pass None
            and state is set to ``preditor.stream.STDOUT`` or ``preditor.stream.STDERR``
            this will automatically be set to the current sys.stdout or sys.stderr.
    """

    def __init__(self, manager, state, old_stream=None, *args, **kwargs):
        super(Director, self).__init__(*args, **kwargs)
        self.manager = manager
        self.state = state

        if old_stream is False:
            old_stream = None
        elif old_stream is None:
            if state == STDOUT:
                old_stream = sys.stdout
            elif state == STDERR:
                old_stream = sys.stderr
        self.old_stream = old_stream

    def close(self):
        if self.old_stream:
            self.old_stream.close()

        super(Director, self).close()

    def flush(self):
        if self.old_stream:
            self.old_stream.flush()

        super(Director, self).flush()

    def write(self, msg):
        self.manager.write(msg, self.state)

        if self.old_stream:
            self.old_stream.write(msg)
