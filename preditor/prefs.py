"""
Module for handling user interface preferences

"""
from __future__ import absolute_import

import os
import sys

# cache of all the preferences
_cache = {}


def backup():
    """Saves a copy of the current preferences to a zip archive."""
    import glob
    import shutil

    archive_base = "preditor_backup_"
    # Save all prefs not just the current core_name.
    prefs = prefs_path()
    # Note: Using parent dir of prefs so we can use shutil.make_archive without
    # backing up the previous backups.
    parent_dir = os.path.join(os.path.dirname(prefs), "_backups")

    # Get the next backup version number to use.
    filenames = glob.glob(os.path.join(parent_dir, "{}*.zip".format(archive_base)))
    version = 1
    if filenames:
        # Add one to the largest version that exists on disk.
        version = int(os.path.splitext(max(filenames))[0].split(archive_base)[-1])
        version += 1

    # Build the file path to save the archive to.
    archive_base = os.path.join(parent_dir, archive_base + "{:04}".format(version))

    # Save the preferences to the given archive name.
    zip_path = shutil.make_archive(archive_base, "zip", prefs)

    return zip_path


def browse(core_name):
    from . import osystem

    path = prefs_path(core_name)
    osystem.explore(path)


def existing():
    """Returns a list of PrEditor preference path names that exist on disk."""
    root = prefs_path()
    return sorted(next(os.walk(root))[1], key=lambda i: i.lower())


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
