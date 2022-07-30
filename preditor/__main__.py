""" Enables support for calling the preditor cli using `python -m preditor`
"""
from __future__ import absolute_import

import sys

import preditor.cli

if __name__ == '__main__':
    # prog_name prevents __main__.py from being shown as the command name in the help
    # text. We don't know the exact command the user passed so we provide a generic
    # `python -m preditor` command.
    sys.exit(preditor.cli.cli(prog_name="python -m preditor"))
