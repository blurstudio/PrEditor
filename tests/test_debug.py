from __future__ import absolute_import

import datetime
import faulthandler
import io
import logging
import os
import subprocess
import sys
import textwrap

import pytest

from preditor import debug


class TestFileLogger:
    def test_clear(self, tmp_path):
        path = tmp_path / 'log.txt'
        path.write_text('Previous session')

        debug.FileLogger(io.StringIO(), str(path))

        assert path.read_text() == ''

    def test_keep_log(self, tmp_path):
        path = tmp_path / 'log.txt'
        path.write_text('Previous session')

        debug.FileLogger(io.StringIO(), str(path), clearLog=False)

        assert path.read_text() == 'Previous session'

    def test_clear_stamp(self, tmp_path, capsys):
        path = tmp_path / 'log.txt'
        path.write_text('Previous session')
        file_logger = debug.FileLogger(io.StringIO(), str(path), clearLog=False)

        file_logger.clear(stamp=True)

        assert path.read_text() == ''
        # The stamp is printed, not written to the log file
        assert capsys.readouterr().out.startswith('--------- Date: ')

    def test_write(self, tmp_path):
        stream = io.StringIO()
        path = tmp_path / 'log.txt'
        file_logger = debug.FileLogger(stream, str(path))

        file_logger.write('First')
        file_logger.write(' second')

        assert path.read_text() == 'First second'
        # The message is also passed along to the stream it replaced
        assert stream.getvalue() == 'First second'

    def test_no_print(self, tmp_path):
        stream = io.StringIO()
        path = tmp_path / 'log.txt'
        file_logger = debug.FileLogger(stream, str(path), _print=False)

        file_logger.write('First')

        assert path.read_text() == 'First'
        assert stream.getvalue() == ''

    def test_newlines(self, tmp_path):
        """Log files use unix style newlines even on windows."""
        path = tmp_path / 'log.txt'
        file_logger = debug.FileLogger(io.StringIO(), str(path))

        file_logger.write('First\nsecond\n')

        assert path.read_bytes() == b'First\nsecond\n'

    def test_flush(self, tmp_path):
        class Stream(io.StringIO):
            flushed = 0

            def flush(self):
                self.flushed += 1

        stream = Stream()
        path = tmp_path / 'log.txt'

        debug.FileLogger(stream, str(path)).flush()
        assert stream.flushed == 1

        # Nothing to flush if there is no old stream
        debug.FileLogger(None, str(path)).flush()

    def test_stamp(self, tmp_path):
        stamp = debug.FileLogger(io.StringIO(), str(tmp_path / 'log.txt')).stamp()

        assert stamp.startswith('--------- Date: ')
        assert str(datetime.date.today()) in stamp
        assert sys.version in stamp

    def test_path_object(self, tmp_path):
        """The log file can be given as a pathlib object or a string."""
        path = tmp_path / 'log.txt'
        file_logger = debug.FileLogger(io.StringIO(), path)

        file_logger.write('First')

        assert path.read_text() == 'First'
        # The path is stored as a string
        assert file_logger._logfile == str(path)


class TestLogToFile:
    @pytest.fixture
    def replace_std(self, monkeypatch):
        """Replaces sys.stdout/sys.stderr so logToFile doesn't affect the tests.

        Call it to replace the streams, it returns the (stdout, stderr) streams
        logToFile will treat as the old streams. This has to be called inside
        the test, pytest replaces sys.stdout/sys.stderr again when it resumes
        capturing output for each phase of the test. monkeypatch restores the
        streams pytest was using once the test finishes.
        """

        def replace():
            stdout, stderr = io.StringIO(), io.StringIO()
            monkeypatch.setattr(sys, 'stdout', stdout)
            monkeypatch.setattr(sys, 'stderr', stderr)
            return stdout, stderr

        return replace

    def test_default(self, replace_std, tmp_path):
        stdout, stderr = replace_std()
        path = tmp_path / 'log.txt'

        debug.logToFile(str(path))

        assert isinstance(sys.stdout, debug.FileLogger)
        assert isinstance(sys.stderr, debug.FileLogger)
        assert sys.stdout.old_stream is stdout
        assert sys.stderr.old_stream is stderr

        print('To stdout')
        sys.stderr.write('To stderr')

        logged = path.read_text()
        # Clearing the log records the date and python version
        assert logged.startswith('--------- Date: ')
        assert sys.version in logged
        # Both streams are logged to the same file
        assert 'To stdout\nTo stderr' in logged
        # And are still written to the streams they replaced
        assert stdout.getvalue().endswith('To stdout\n')
        assert stderr.getvalue() == 'To stderr'

    def test_stdout_only(self, replace_std, tmp_path):
        stdout, stderr = replace_std()
        path = tmp_path / 'log.txt'

        debug.logToFile(str(path), stderr=False)

        assert isinstance(sys.stdout, debug.FileLogger)
        assert sys.stderr is stderr

    def test_stderr_only(self, replace_std, tmp_path):
        stdout, stderr = replace_std()
        path = tmp_path / 'log.txt'

        debug.logToFile(str(path), stdout=False)

        assert sys.stdout is stdout
        assert isinstance(sys.stderr, debug.FileLogger)
        # The stamp is only written when stdout is replaced
        assert path.read_text() == ''

    def test_no_old_std(self, replace_std, tmp_path):
        stdout, stderr = replace_std()
        path = tmp_path / 'log.txt'

        debug.logToFile(str(path), useOldStd=False)

        print('To stdout')
        sys.stderr.write('To stderr')

        assert 'To stdout\nTo stderr' in path.read_text()
        # Nothing is written to the streams that were replaced
        assert stdout.getvalue() == ''
        assert stderr.getvalue() == ''

    def test_keep_log(self, replace_std, tmp_path):
        replace_std()
        path = tmp_path / 'log.txt'
        path.write_text('Previous session\n')

        debug.logToFile(str(path), clearLog=False)
        print('To stdout')

        logged = path.read_text()
        assert logged.startswith('Previous session\n')
        # The stamp is only written when the log is cleared
        assert '--------- Date: ' not in logged

    def test_stream_handlers(self, replace_std, tmp_path):
        """StreamHandlers using the replaced streams point at the FileLogger."""
        stdout, stderr = replace_std()
        path = tmp_path / 'log.txt'
        root = logging.getLogger()
        handlers = {
            'stdout': logging.StreamHandler(stdout),
            'stderr': logging.StreamHandler(stderr),
            'other': logging.StreamHandler(io.StringIO()),
        }
        for handler in handlers.values():
            root.addHandler(handler)

        try:
            debug.logToFile(str(path))

            assert handlers['stdout'].stream is sys.stdout
            assert handlers['stderr'].stream is sys.stderr
            # Handlers using any other stream are left alone
            assert handlers['other'].stream is not sys.stdout
            assert handlers['other'].stream is not sys.stderr
        finally:
            for handler in handlers.values():
                root.removeHandler(handler)

    def test_path_object(self, replace_std, tmp_path):
        """The log file can be given as a pathlib object or a string."""
        replace_std()
        path = tmp_path / 'log.txt'

        debug.logToFile(path)
        print('To stdout')

        assert 'To stdout' in path.read_text()
        # Both FileLogger's store the path as a string
        assert sys.stdout._logfile == str(path)
        assert sys.stderr._logfile == str(path)


class TestFaulthandlerToFile:
    # Installs faulthandler in a subprocess and crashes it. Run as a subprocess
    # so the crash and faulthandler's process wide state don't affect the tests.
    CRASH_SCRIPT = textwrap.dedent(
        """
        import ctypes
        import sys

        from preditor import debug

        log, std = sys.argv[1], sys.argv[2]
        if std:
            # faulthandler can't write to the FileLogger logToFile installs, it
            # needs a file descriptor, so it has to open its own file.
            debug.logToFile(std)

        assert debug.faulthandlerToFile(log) is True

        # Dereference a null pointer. Python can't catch this, the traceback is
        # only recorded because faulthandler was installed.
        ctypes.string_at(0)
        """
    )

    @pytest.fixture
    def enable_calls(self, monkeypatch):
        """Records faulthandler.enable calls instead of installing it for real.

        Actually installing faulthandler would replace the file pytest installed
        it with for the rest of the test session.
        """
        calls = []

        def enable(file=None, all_threads=True):
            calls.append({'file': file, 'all_threads': all_threads})

        monkeypatch.setattr(faulthandler, 'is_enabled', lambda: bool(calls))
        monkeypatch.setattr(faulthandler, 'enable', enable)
        # monkeypatch restores the module variable, but not the open file object
        monkeypatch.setattr(debug, '_faulthandlerFile', None)

        yield calls

        for call in calls:
            call['file'].close()

    def test_install(self, enable_calls, tmp_path):
        path = tmp_path / 'faulthandler.log'

        assert debug.faulthandlerToFile(str(path)) is True
        assert path.exists()

        assert len(enable_calls) == 1
        assert enable_calls[0]['file'].name == str(path)
        assert enable_calls[0]['all_threads'] is True

        # The file is kept open, faulthandler writes to its file descriptor
        assert debug._faulthandlerFile is enable_calls[0]['file']
        assert debug._faulthandlerFile.closed is False

    def test_all_threads(self, enable_calls, tmp_path):
        debug.faulthandlerToFile(str(tmp_path / 'faulthandler.log'), allThreads=False)

        assert enable_calls[0]['all_threads'] is False

    def test_already_enabled(self, enable_calls, tmp_path, monkeypatch):
        monkeypatch.setattr(faulthandler, 'is_enabled', lambda: True)
        path = tmp_path / 'faulthandler.log'

        assert debug.faulthandlerToFile(str(path)) is False
        # Nothing was installed and the log file was not created
        assert enable_calls == []
        assert not path.exists()
        assert debug._faulthandlerFile is None

    def test_force(self, enable_calls, tmp_path):
        first = tmp_path / 'first.log'
        second = tmp_path / 'second.log'

        assert debug.faulthandlerToFile(str(first)) is True
        # Now that faulthandler is enabled the second call is ignored
        assert debug.faulthandlerToFile(str(second)) is False
        assert not second.exists()

        assert debug.faulthandlerToFile(str(second), force=True) is True
        assert len(enable_calls) == 2
        assert debug._faulthandlerFile is enable_calls[1]['file']
        # The file used by the previous call is no longer needed
        assert enable_calls[0]['file'].closed is True

    def test_clear_log(self, enable_calls, tmp_path):
        path = tmp_path / 'faulthandler.log'
        path.write_text('Previous crash')
        assert path.read_text() == 'Previous crash'

        debug.faulthandlerToFile(str(path))

        assert path.read_text() == ''

    def test_clear_log_disabled(self, enable_calls, tmp_path):
        path = tmp_path / 'faulthandler.log'
        path.write_text('Previous crash')

        debug.faulthandlerToFile(str(path), clearLog=False)

        assert path.read_text() == 'Previous crash'

    def test_path_object(self, enable_calls, tmp_path):
        """The log file can be given as a pathlib object or a string."""
        path = tmp_path / 'faulthandler.log'

        assert debug.faulthandlerToFile(path) is True

        assert path.exists()
        # open records the path it was given as a string
        assert enable_calls[0]['file'].name == str(path)

    @pytest.mark.parametrize('log_to_file', (False, True))
    def test_crash_logged(self, tmp_path, log_to_file):
        """A crash python can't report is written to the faulthandler log file."""
        path = tmp_path / 'faulthandler.log'
        script = tmp_path / 'crash.py'
        script.write_text(self.CRASH_SCRIPT)

        env = dict(os.environ)
        # Ensure the subprocess can import preditor even if its not installed
        root = os.path.dirname(os.path.dirname(os.path.abspath(debug.__file__)))
        env['PYTHONPATH'] = os.pathsep.join(
            [root] + [p for p in [env.get('PYTHONPATH')] if p]
        )
        # faulthandler being enabled by the env var would disable the install
        env.pop('PYTHONFAULTHANDLER', None)
        std = str(tmp_path / 'std.log') if log_to_file else ''

        subprocess.call(
            [sys.executable, str(script), str(path), std],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        output = path.read_text()
        assert 'Current thread' in output
        assert 'crash.py' in output
