from __future__ import absolute_import

import io
import sys

import pytest

from preditor.stream import STDERR, STDOUT, Director, Manager, install_to_std


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
    stdout_director = Director(manager, STDOUT)
    stderr_director = Director(manager, STDERR)

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
        nullout_director = Director(manager, STDOUT)
        nullerr_director = Director(manager, STDERR)
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

    # Base check that default kwargs work as expected
    assert manager.store_writes is True  # disable_writes
    assert len(manager) == 1  # clear
    assert len(bound.data) == 0  # replay
    manager.add_callback(bound.write)
    assert manager.store_writes is True  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 0  # replay

    manager.add_callback(bound.write, disable_writes=True)
    assert manager.store_writes is False  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 0  # replay

    manager.add_callback(bound.write, replay=True)
    assert manager.store_writes is False  # disable_writes
    assert len(manager) == 1  # Clear
    assert len(bound.data) == 1  # replay

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
