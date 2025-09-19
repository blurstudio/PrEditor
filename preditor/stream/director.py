from __future__ import absolute_import, print_function

import io
import sys

from . import STDERR, STDOUT


class _DirectorBuffer(io.RawIOBase):
    """Binary buffer that forwards text writes to the manager.

    This makes the stream more compatible including if enabled when running tox.

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
        name (str, optional): Stored on self.name.
    """

    def __init__(self, manager, state, old_stream=None, name='nul'):
        super().__init__()
        self.manager = manager
        self.state = state
        self.old_stream = old_stream
        self.name = name

    def flush(self):
        if self.old_stream:
            self.old_stream.flush()
        super().flush()

    def writable(self):
        return True

    def write(self, b):
        if isinstance(b, memoryview):
            b = b.tobytes()

        # Decode incoming bytes (TextIOWrapper encodes before sending here)
        msg = b.decode("utf-8", errors="replace")
        self.manager.write(msg, self.state)

        if self.old_stream:
            self.old_stream.write(msg)

        return len(b)


class Director(io.TextIOWrapper):
    """A file like object that stores the text written to it in a manager.
    This manager can be shared between multiple Directors to build a single
    continuous history of all writes.

    While this uses a buffer under the hood, buffering is disabled and any calls
    to write will automatically flush the buffer.

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
        # Keep track of whether we wrapped a std stream
        # that way we don't .close() any streams that we don't control
        self.std_stream_wrapped = False

        name = 'nul'
        if old_stream is False:
            old_stream = None
        elif old_stream is None:
            if state == STDOUT:
                # On Windows if we're in pythonw.exe, then sys.stdout is named "nul"
                # And it uses cp1252 encoding (which breaks with unicode)
                # So if we find this nul TextIOWrapper, it's safe to just skip it
                name = getattr(sys.stdout, 'name', '')
                if name != 'nul':
                    self.std_stream_wrapped = True
                    old_stream = sys.stdout
            elif state == STDERR:
                name = getattr(sys.stderr, 'name', '')
                if name != 'nul':
                    self.std_stream_wrapped = True
                    old_stream = sys.stderr

        self.old_stream = old_stream
        self.manager = manager
        self.state = state

        # Build the buffer. This provides the expected interface for tox, etc.
        raw = _DirectorBuffer(manager, state, old_stream, name)
        buffer = io.BufferedWriter(raw)

        super().__init__(buffer, encoding="utf-8", write_through=True, *args, **kwargs)

    def __repr__(self):
        return f"<Director state={self.state} old_stream={self.old_stream!r}>"

    def close(self):
        if (
            self.old_stream
            and not self.std_stream_wrapped
            and self.old_stream is not sys.__stdout__
            and self.old_stream is not sys.__stderr__
        ):
            self.old_stream.close()

        super().close()

    def write(self, msg):
        super().write(msg)
        # Force a write of any buffered data
        self.flush()

    # These methods enable terminal features like color coding etc.
    def isatty(self):
        if self.old_stream is not None:
            return self.old_stream.isatty()
        return False

    @property
    def encoding(self):
        if self.old_stream is not None:
            return self.old_stream.encoding
        return super().encoding

    @property
    def errors(self):
        if self.old_stream is not None:
            return self.old_stream.errors
        return super().errors
