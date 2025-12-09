import errno
import json
import os
import sys
import traceback
from pathlib import Path


class Json:
    """Load a json file with a better tracebacks if something goes wrong.

    Args:
        filename (pathlib.Path): The path to the file being loaded/parsed. Unless
            `json_str` is also provided load will use `json.load` to parse the
            contents of this json file.
        json_str (str, optional): If provided then uses `json.loads` to parse
            this value. `filename` must be provided and will be included in any
            exceptions that are raised parsing this text.
    """

    def __init__(self, filename, json_str=None):
        if isinstance(filename, str):
            filename = Path(filename)
        self.filename = filename
        self.json_str = json_str

    @classmethod
    def _load_json(cls, source, load_funct, *args, **kwargs):
        """Work function that parses json and ensures any errors report the source.

        Args:
            source (os.PathLike or str): The source of the json data. This is
                reported in any raised exceptions.
            load_funct (callable): A function called to parse the json data.
                Normally this is `json.load` or `json.loads`.
            *args: Arguments passed to `load_funct`.
            *kwargs: Keyword arguments passed to `load_funct`.

        Raises:
            FileNotFoundError: If filename is not pointing to a file that
                actually exists.
            ValueError: The error raised due to invalid json.
        """
        try:
            return load_funct(*args, **kwargs)
        except ValueError as e:
            # Using python's native json parser
            msg = f'{e} Source("{source}")'
            raise type(e)(msg, e.doc, e.pos).with_traceback(sys.exc_info()[2]) from None

    def load(self):
        """Parse and return self.json_str if defined otherwise self.filename."""
        if self.json_str:
            return self.loads_json(self.json_str, self.filename)
        return self.load_json_file(self.filename)

    @classmethod
    def load_json_file(cls, filename):
        """Open and parse a json file. If a parsing error happens the file path
        is added to the exception to allow for easier debugging.

        Args:
            filename (pathlib.Path): A existing file path.

        Returns:
            The data stored in the json file.

        Raises:
            FileNotFoundError: If filename is not pointing to a file that
                actually exists.
            ValueError: The error raised due to invalid json.
        """
        if not filename.is_file():
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), str(filename)
            )

        with filename.open() as fle:
            data = cls._load_json(filename, json.load, fle)
        return data

    @classmethod
    def loads_json(cls, json_str, source):
        """Open and parse a json string. If a parsing error happens the source
        file path is added to the exception to allow for easier debugging.

        Args:
            json_str (str): The json data to parse.
            source (pathlib.Path): The location json_str was pulled from.
                This is reported if any parsing errors happen.

        Returns:
            The data stored in the json file.

        Raises:
            FileNotFoundError: If filename is not pointing to a file that
                actually exists.
            ValueError: The error raised due to invalid json.
        """
        return cls._load_json(source, json.loads, json_str)


class ShellPrint:
    """Utilities to print to sys.__stdout__/__stderr__ bypassing the PrEditor streams.

    This allows you to write to the host console instead of PrEditor's interface.
    This helps when developing for the stream or console classes if you cause an
    exception you might get no traceback printed to debug otherwise.

    On windows if using gui mode app(pythonw.exe) that doesn't have a console
    the methods will not print anything and just return False. If possible switch
    to using python.exe or install another file stream like `preditor.debug.FileLogger`,
    but they will need to be installed on `sys.__stdout__/__stderr__`.
    """

    def __init__(self, error=False):
        self.error = error

    def print(self, *args, **kwargs):
        """Prints to the shell."""
        if "file" in kwargs:
            raise KeyError(
                "file can not be passed to `ShellPrint.print`. Instead use error."
            )
        # Check for pythonw.exe's lack of streams and exit
        kwargs["file"] = self.stream
        if kwargs["file"] is None:
            """Note: This protects against errors like this when using pythonw
              File "preditor/stream/director.py", line 124, in write
                super().write(msg)
            RuntimeError: reentrant call inside <_io.BufferedWriter name='nul'>
            """
            return False

        # Print to the host stream
        print(*args, **kwargs)
        return True

    def print_exc(self, msg, limit=None, chain=True, width=79):
        """Prints a header line, the current exception and a footer line to shell.

        This must be called from inside of a try/except statement.
        """
        stream = self.stream
        if stream is None:
            return False

        print(f" {msg} ".center(width, "-"), file=sys.__stderr__)
        traceback.print_exc(limit=limit, file=stream, chain=chain)
        print(f" {msg} ".center(width, "-"), file=sys.__stderr__)
        return True

    @property
    def stream(self):
        if self.error:
            return sys.__stderr__
        return sys.__stdout__


class Truncate:
    def __init__(self, text, sep='...'):
        self.text = text
        self.sep = sep
        self.sep_spaces = f' {sep} '

    def middle(self, n=100):
        """Truncates the provided text to a fixed length, putting the sep in the middle.
        https://www.xormedia.com/string-truncate-middle-with-ellipsis/
        """
        if len(self.text) <= n:
            # string is already short-enough
            return self.text
        # half of the size, minus the seperator
        n_2 = int(n) // 2 - len(self.sep_spaces)
        # whatever's left
        n_1 = n - n_2 - len(self.sep_spaces)
        return '{0}{1}{2}'.format(self.text[:n_1], self.sep_spaces, self.text[-n_2:])

    def lines(self, max_lines=20):
        """Truncates the provided text to a maximum number of lines with a separator
        at the end if required.
        """
        lines = self.text.split("\n")
        orig_len = len(lines)
        lines = lines[:max_lines]
        trim_len = len(lines)
        if orig_len != trim_len:
            lines.append("...")
        truncated = "\n".join(lines)

        return truncated
