from __future__ import absolute_import

import datetime
import io
import logging
import sys

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
