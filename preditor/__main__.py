""" Enables support for calling the blurdev cli using `python -m blurdev`
"""

from __future__ import absolute_import

import sys
import blurdev.cli

if __name__ == '__main__':
    # prog_name prevents __main__.py from being shown as the command name in the help
    # text. We don't know the exact command the user passed so we provide a generic
    # `python -m blurdev` command.
    sys.exit(blurdev.cli.main(prog_name="python -m blurdev"))
