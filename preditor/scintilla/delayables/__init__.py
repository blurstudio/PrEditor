from __future__ import absolute_import, print_function

from . import smart_highlight, spell_check

# Import the base classes used to make most Delayables
# TODO: Make these imports a plugin based system of some sort.

__all__ = [
    "smart_highlight",
    "spell_check",
]
