from __future__ import absolute_import

import io
import logging
import sys
import traceback

import pytest

from preditor import utils
from preditor.constants import StreamType
from preditor.stream import Director, Manager, install_to_std


@pytest.fixture
def manager():
    return Manager()


@pytest.fixture
def stdout(manager):
    old_stream = io.StringIO()
    return Director(manager, "test_out", old_stream=old_stream)


@pytest.fixture
def stderr(manager):
    old_stream = io.StringIO()
    return Director(manager, "test_err", old_stream=old_stream)


class Bound(object):
    def __init__(self):
        self.data = []

    def write(self, msg, state):
        self.data.append((msg, state))


def test_get_value(manager, stdout, stderr):
    stdout.write(u'Written to stdout')
    stderr.write(u'Written to stderr')

    check = '[test_out:Written to stdout][test_err:Written to stderr]'
    assert check == manager.get_value()


def test_no_old_stream(manager):
    director = Director(manager, "test_out", old_stream=False)
    assert director.old_stream is None


def test_nul_stream(manager):
    # I can't set the `name` prop of a regular TextIOWrapper
    # So I need this subclass so I can mock the pythonw
    # standard out/err streams
    class NamedTextIOWrapper(io.TextIOWrapper):
        def __init__(self, buffer, name=None, **kwargs):
            vars(self)['name'] = name
            super().__init__(buffer, **kwargs)

        def __getattribute__(self, name):
            if name == 'name':
                return vars(self)['name']
            return super().__getattribute__(name)

    # Make directors that wrap sys.stdout and sys.stderr
    # This way we can check that the default behavior works
    stdout_director = Director(manager, StreamType.STDOUT)
    stderr_director = Director(manager, StreamType.STDERR)

    # Wrap the stdout/stderr directors so we can check that
    # director.std_stream_wrapped is not set for these cases
    wrapout_director = Director(manager, 'test_wrapout', old_stream=stdout_director)
    wraperr_director = Director(manager, 'test_wraperr', old_stream=stdout_director)

    # Back up sys.stdout/stderr and replace them with my own streams that replicate
    # the name/encoding of the windows pythonw.exe default streams
    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    sys.stdout = NamedTextIOWrapper(io.BytesIO(), name='nul', encoding='cp1252')
    sys.stderr = NamedTextIOWrapper(io.BytesIO(), name='nul', encoding='cp1252')
    try:
        # Build a director here that will grab the nul streams
        # so we can check that they don't store them in .old_stream
        nullout_director = Director(manager, StreamType.STDOUT)
        nullerr_director = Director(manager, StreamType.STDERR)
    finally:
        # And make sure to restore the backed up stdout
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

    assert nullout_director.old_stream is None
    assert nullerr_director.old_stream is None
    assert stdout_director.old_stream is sys.stdout
    assert stderr_director.old_stream is sys.stderr

    assert stdout_director.std_stream_wrapped
    assert stderr_director.std_stream_wrapped
    assert not nullout_director.std_stream_wrapped
    assert not nullerr_director.std_stream_wrapped
    assert not wrapout_director.std_stream_wrapped
    assert not wraperr_director.std_stream_wrapped


def test_callback(manager, stdout, stderr):
    data = []

    def callback(msg, state):
        data.append((msg, state))

    stdout.write(u'stdout 1')
    stderr.write(u'stderr 1')

    manager.add_callback(callback)
    assert callback in manager.callbacks
    assert len(manager.callbacks) == 1

    # Vanilla weakrefs doesn't work well with bound methods, so check that
    # adding a bound method callback is respected.
    bound = Bound()
    manager.add_callback(bound.write)
    assert bound.write in manager.callbacks
    assert len(manager.callbacks) == 2

    stdout.write(u'stdout 2')
    stderr.write(u'stderr 2')

    manager_check = [
        ('stdout 1', 'test_out'),
        ('stderr 1', 'test_err'),
        ('stdout 2', 'test_out'),
        ('stderr 2', 'test_err'),
    ]

    data_check = [
        ('stdout 2', 'test_out'),
        ('stderr 2', 'test_err'),
    ]

    assert list(manager) == manager_check
    assert data == data_check

    # Disable adding data to the manager
    manager.store_writes = False

    stderr.write(u'stderr 3')
    stdout.write(u'stdout 3')

    # Check that store_writes was respected and callback was called
    assert list(manager) == manager_check
    data_check.append(('stderr 3', 'test_err'))
    data_check.append(('stdout 3', 'test_out'))
    assert data == data_check

    # Check that we can remove callbacks
    assert len(manager.callbacks) == 2
    manager.remove_callback(callback)
    assert len(manager.callbacks) == 1
    assert callback not in manager.callbacks

    manager.remove_callback(bound.write)
    assert len(manager.callbacks) == 0


def test_add_callback(manager, stdout, stderr):
    """Check that all of the add_callback kwargs work as expected"""
    stdout.write(u'some text')
    bound = Bound()

    def remove_callback():
        manager.remove_callback(bound.write)
        assert bound.write not in manager.callbacks

    # Base check that default kwargs work as expected
    assert manager.store_writes is True  # disable_writes
    assert len(manager) == 1  # clear
    assert len(bound.data) == 0  # replay
    assert bound.write not in manager.callbacks
    manager.add_callback(bound.write)
    assert bound.write in manager.callbacks
    assert manager.store_writes is True  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 0  # replay

    remove_callback()
    manager.add_callback(bound.write, disable_writes=True)
    assert manager.store_writes is False  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 0  # replay

    remove_callback()
    manager.add_callback(bound.write, replay=True)
    assert manager.store_writes is False  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 1  # replay

    remove_callback()
    manager.add_callback(bound.write, clear=True)
    assert manager.store_writes is False  # disable_writes
    assert len(manager) == 0  # Clear
    assert len(bound.data) == 1  # replay


def test_install_to_std():
    """Check the install_to_std convenience function."""
    # install_to_std replaces sys.stdout/err, which may break pytest. Backup and
    # restore the original FLO's so we don't break other tests.
    stdout = sys.stdout
    stderr = sys.stderr
    temp_out = io.StringIO()
    temp_err = io.StringIO()
    sys.stdout = temp_out
    sys.stderr = temp_err
    try:
        manager = install_to_std()
        old_out = sys.stdout.old_stream
        old_err = sys.stderr.old_stream
        inst_out = isinstance(sys.stdout, Director)
        inst_err = isinstance(sys.stderr, Director)
        # Ensure that flush gets called while testing
        sys.stdout.flush()
    finally:
        sys.stdout = stdout
        sys.stderr = stderr

    # Now that we have restored stdout/err, do all of the checks so we know the
    # output is sent to pytest's stdout/err.
    assert old_out == temp_out
    assert old_err == temp_err
    assert inst_out
    assert inst_err
    assert isinstance(manager, Manager)


@pytest.mark.parametrize(
    "input,check",
    (
        (["preditor.cli"], ["preditor.cli", None, "Console", None]),
        (["preditor.cli,INFO"], ["preditor.cli", 20, "Console", None]),
        (["preditor.prefs,30"], ["preditor.prefs", 30, "Console", None]),
        (["preditor.cli,lvl=30"], ["preditor.cli", 30, "Console", None]),
        (["preditor.cli,level=WARNING"], ["preditor.cli", 30, "Console", None]),
        # Test escaping and complex formatter strings
        (["preditor,formatter=%(msg)s"], ["preditor", None, "Console", "%(msg)s"]),
        (["preditor,fmt=%(msg)s,POST"], ["preditor", None, "Console", "%(msg)s,POST"]),
        ([r"preditor,fmt=M\=%(msg)s"], ["preditor", None, "Console", "M=%(msg)s"]),
        ([r"preditor,fmt=M\\=%(msg)s"], ["preditor", None, "Console", r"M\=%(msg)s"]),
        (
            [r"preditor,fmt=M\=%(msg)s,POST"],
            ["preditor", None, "Console", "M=%(msg)s,POST"],
        ),
        (
            [r"plug=PrEditor,fmt=A\=%(msg)sG\=G,level=WARNING,name=six"],
            ["six", 30, "PrEditor", "A=%(msg)sG=G"],
        ),
        # Order of kwargs doesn't matter and there are no trailing commas
        (
            [r"plug=PrEditor,fmt=A\=%(msg)s,G\=G,level=WARNING,name=six"],
            ["six", 30, "PrEditor", "A=%(msg)s,G=G"],
        ),
        (
            [r"plug=PrEditor,fmt=A\=%(msg)s,G\=G,B,level=WARNING,name=six"],
            ["six", 30, "PrEditor", "A=%(msg)s,G=G,B"],
        ),
    ),
)
def test_handler_info(input, check):
    from preditor.stream.console_handler import HandlerInfo

    hi = HandlerInfo(*input)
    assert hi.name == check[0]
    assert hi.level == check[1]
    assert hi.plugin == check[2]
    assert isinstance(hi.formatter, logging.Formatter)
    if check[3] is None:
        # Treat None as the default formatter
        check[3] = HandlerInfo._default_format
    assert hi.formatter._fmt == check[3]


class TestShellPrint:
    def patch(self, monkeypatch, pyw):
        # Replace all 4 streams with tracking streams
        new_out = io.StringIO()
        new_err = io.StringIO()
        if pyw:
            # or None if simulating pythonw
            new_out_ = None
            new_err_ = None
        else:
            # If the console exists a stream is actually used
            new_out_ = io.StringIO()
            new_err_ = io.StringIO()

        monkeypatch.setattr(sys, "stdout", new_out)
        monkeypatch.setattr(sys, "stderr", new_err)
        monkeypatch.setattr(sys, "__stdout__", new_out_)
        monkeypatch.setattr(sys, "__stderr__", new_err_)

        return new_out, new_err, new_out_, new_err_

    def test_print_none(self, monkeypatch, capsys):
        """Verify that the print command works as expected. If `sys.__std*__`
        is None (pythonw.exe on windows) it will write to `sys.stdout`.
        """
        # Simulate pythonw.exe on windows, which uses None for sys.__std*__
        monkeypatch.setattr(sys, "__stdout__", None)
        monkeypatch.setattr(sys, "__stderr__", None)

        # Print to the various streams
        print("stdout")
        print("stdout: None", file=sys.__stdout__)
        print("stderr", file=sys.stderr)
        print("stderr: None", file=sys.__stderr__)

        # Verify the prints were written to the expected stream
        captured = capsys.readouterr()
        # sys.stdout and None are sent to sys.stdout
        assert captured.out == "stdout\nstdout: None\nstderr: None\n"
        # Only sys.stderr gets written to sys.stderr
        assert captured.err == "stderr\n"

    @pytest.mark.parametrize("pyw", (True, False))
    def test_print(self, monkeypatch, pyw):
        # Replace all 4 streams with tracking streams
        new_out, new_err, new_out_, new_err_ = self.patch(monkeypatch, pyw)

        # Regular write/print calls go to stdout/stderr
        print("stdout")
        print("stderr", file=sys.stderr)
        # Use ShellPrint to write to `__std*__` and make sure it only returns
        # True if it should be writting to that stream.
        assert utils.ShellPrint().print("__stdout__") is not pyw
        assert utils.ShellPrint(error=True).print("__stderr__") is not pyw

        # Verify the prints were written to the expected stream or discarded
        assert new_out.getvalue() == "stdout\n"
        assert new_err.getvalue() == "stderr\n"
        if not pyw:
            assert new_out_.getvalue() == "__stdout__\n"
            assert new_err_.getvalue() == "__stderr__\n"

    @pytest.mark.parametrize("pyw", (True, False))
    def test_print_exc(self, monkeypatch, pyw):
        # Replace all 4 streams with tracking streams
        new_out, new_err, new_out_, new_err_ = self.patch(monkeypatch, pyw)

        # Capture an exception and print it using ShellPrint
        try:
            raise RuntimeError("Test exception")
        except RuntimeError:
            check = traceback.format_exc()
            assert utils.ShellPrint(error=True).print_exc("A Test") is not pyw

        # Verify that the text was only written to `sys.__stderr__` unless
        # that is None
        assert new_out.getvalue() == ""
        assert new_err.getvalue() == ""
        if not pyw:
            assert new_out_.getvalue() == ""
            assert new_err_.getvalue() == "\n".join(
                [
                    " A Test ".center(79, "-"),
                    check.rstrip(),
                    " A Test ".center(79, "-"),
                    "",
                ]
            )
