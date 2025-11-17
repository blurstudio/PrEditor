import enum


class StreamType(enum.Flag):
    """Different types of streams used by PrEditor."""

    STDERR = enum.auto()
    STDIN = enum.auto()
    STDOUT = enum.auto()
    CONSOLE = enum.auto()
    """Write directly to the console ignoring STDERR/STDOUT filters."""
    RESULT = enum.auto()
    """Write directly to ConsolePrEdit's result output without using  stdout/err."""
