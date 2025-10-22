import errno
import json
import os
import sys
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
