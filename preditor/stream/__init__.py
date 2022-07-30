""" A system for capturing stream output and later inserting the captured output into a
gui, and allowing that GUI to directly capture any new output written to the streams.

A use case for this is to attach a Manager's as early as possible to ``sys.stdout``
and ``sys.stderr`` process, before any GUI's are created. Then later you initialize a
GUI python console that should show all python output that has already been written.
Any future writes are delivered directly to the gui using a callback mechanism.

Example::

    # Startup script or plugin for DCC runs this as early as possible.
    from preditor.stream import install_to_std

    manager = install_to_std()
    # Startup script exits and DCC continues to load eventually creating the main gui.

    # From a menu a user chooses to show a custom console(A gui that replicates a
    # python interactive console inside the DCC).
    console = PythonConsole()

    # We will want to see all the previous writes made by python, so replay them
    # in the console so it can properly handle stdout and stderr writes.
    for msg, state in manager:
        console.write(msg, state)

    # Make it so any future writes are automatically added to the console.
    manager.add_callback(console.write)

    # Optionally, disable storing data in the buffer. buffer.write calls will now
    # directly write to console so there is no reason to duplicate the data to the
    # buffer.
    manager.append_writes = False
"""
from __future__ import absolute_import, print_function

import sys

STDERR = 1
STDIN = 2
STDOUT = 3

from .director import Director  # noqa: E402
from .manager import Manager  # noqa: E402

"""Set when :py:attr:``install_to_std`` is called. This stores the installed Manager
so it can be accessed to install callbacks.
"""
active = None

__all__ = [
    "active",
    "Director",
    "install_to_std",
    "Manager",
    "STDERR",
    "STDIN",
    "STDOUT",
]


def install_to_std(out=True, err=True):
    """Replaces ``sys.stdout`` and ``sys.stderr`` with :py:class:`Director`'s
    using the returned :py:class:`Manager`. This manager is stored as the ``active``
    variable and can be accessed later. This can be called more than once, and it will
    simply return the already installed Manager.

    Args:
        out (bool, optional): Enables replacement of ``sys.stdout`` on first call.
        err (bool, optional): Enables replacement of ``sys.stderr`` on first call.
    """
    global active

    if active is None:
        active = Manager()
        if out:
            sys.stdout = Director(active, STDOUT)
        if err:
            sys.stderr = Director(active, STDERR)

    return active
