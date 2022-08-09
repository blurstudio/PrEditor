"""
Module for handling user interface preferences

"""
from __future__ import absolute_import

import os
import sys

# cache of all the preferences
_cache = {}


def prefs_path(filename=None, core_name=None):
    """The path PrEditor's preferences are saved as a json file.

    The enviroment variable `PREDITOR_PREF_PATH` is used if set, otherwise
    it is saved in one of the user folders.
    """
    if "PREDITOR_PREF_PATH" in os.environ:
        ret = os.environ["PREDITOR_PREF_PATH"]
    else:
        if sys.platform == "win32":
            ret = "%appdata%/blur/preditor"
        else:
            ret = "$HOME/.blur/preditor"
    ret = os.path.normpath(os.path.expandvars(os.path.expanduser(ret)))
    if core_name:
        ret = os.path.join(ret, core_name)
    if filename:
        ret = os.path.join(ret, filename)
    return ret
