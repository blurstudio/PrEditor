"""
Module for handling user interface preferences

"""
from __future__ import absolute_import

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

from . import resourcePath, utils

# cache of all the preferences
_cache = {}

DATETIME_FORMAT = "%Y-%m-%d-%H-%M-%S-%f"
DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{6}")


class VersionTypes:
    """Nice names for the workbox version types."""

    First = 0
    Previous = 1
    Next = 2
    TwoBeforeLast = 3
    Last = 4


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


def get_full_path(core_name, workbox_id, backup_file=None):
    """Get the full path for the given workbox_id in the given core. If
    backup_file is provided, use that.

    Args:
        core_name (str): The current core_name
        workbox_id (str): The current workbox_id
        backup_file (str, optional): The backup_file (ie with time stamped path)

    Returns:
        full_path (str): The constructed full path
    """
    workbox_dir = get_prefs_dir(core_name)
    workbox_dir = get_prefs_dir(core_name=core_name)
    if backup_file:
        full_path = Path(workbox_dir) / backup_file
    else:
        full_path = Path(workbox_dir) / workbox_id / workbox_id
        full_path = str(full_path.with_suffix(".py"))
    return full_path


def get_relative_path(core_name, path):
    """Get the file path relative to the current core's prefs path. If path is
    not relative to working_dir, return the original path

    Args:
        core_name (str): The current core_name
        path (str): The full path

    Returns:
        rel_path (rel_path): The determined relative path.
    """
    workbox_dir = get_prefs_dir(core_name)
    workbox_dir = get_prefs_dir(core_name=core_name)
    try:
        rel_path = str(Path(path).relative_to(workbox_dir))
    except ValueError:
        rel_path = path
    return rel_path


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


def get_prefs_dir(sub_dir='workboxes', core_name=None, create=False):
    """Get the prefs path including the given sub directory, and optionally
    create the file on disk.

    Args:
        sub_dir (str, optional): The needed sub directory, defaults to 'workboxes'
        core_name (str, optional): The current core_name
        create (bool, optional): Whether to create directories on disk

    Returns:
        prefs_dir (str): The determined path
    """
    prefs_dir = prefs_path(sub_dir, core_name=core_name)
    if create:
        Path(prefs_dir).mkdir(parents=True, exist_ok=True)
    return prefs_dir


def create_stamped_path(core_name, filepath, sub_dir='workboxes', time_str=None):
    """For the given filepath, generate a filepath which includes a time stamp,
    which is either based on the current time, or passed explicitly (ie to
    re-order backups when prefs are saved in another instance of PrEditor in the
    same core.

    Args:
        core_name (str): The current core_name
        filepath (str): The filepath we need to create a time-stamped path for
        sub_dir (str, optional): The needed sub directory, defaults to 'workboxes'
        time_str (None, optional): A specific time-stamp to use, otherwise generate
            a new one from current time.

    Returns:
        path (str): The created stamped path
    """
    path = Path(get_prefs_dir(sub_dir=sub_dir, core_name=core_name, create=True))
    filepath = Path(filepath)
    stem = filepath.stem
    name = filepath.name
    suffix = filepath.suffix or ".py"

    if sub_dir == "workboxes":
        path = path / stem

    if not time_str:
        now = datetime.datetime.now()
        time_str = now.strftime(DATETIME_FORMAT)
    name = "{}-{}".format(stem, time_str)

    path = path / name
    path = path.with_suffix(suffix)

    path.parent.mkdir(exist_ok=True)

    path = str(path)
    return path


def get_file_group(core_name, workbox_id):
    """Get the backup files for the given workbox_id, for the given core_name

    Args:
        core_name (str): The current core_name
        workbox_id (str): The current workbox_id

    Returns:
        files (list): The list of files found for the given workbox_id
    """
    directory = Path(get_prefs_dir(core_name=core_name, sub_dir='workboxes'))
    workbox_dir = directory / workbox_id
    workbox_dir.mkdir(exist_ok=True)
    files = sorted(list(workbox_dir.iterdir()))
    return files


def get_backup_file_index_and_count(core_name, workbox_id, backup_file, files=None):
    """For the given core_name and workbox_id, find the (zero-based)index
    backup_file is within that workbox's backup files, plus the total count of
    backup files.

    Args:
        core_name (str): The current core_name
        workbox_id (str): The current workbox_id
        backup_file (None, optional): The currently loaded backup file.
        files (None, optional): If we already found the files on disk, pass them
            in here
    Returns:
        idx, count (int, int): The zero-based index of backup_file, and file count
    """
    idx = None
    files = files or get_file_group(core_name, workbox_id)
    count = len(files)
    if not files:
        return None, None

    backup_file = Path(backup_file) if backup_file else None
    if not backup_file:
        return None, None

    backup_file = get_full_path(core_name, workbox_id, backup_file)
    backup_file = Path(backup_file)

    if backup_file in files:
        idx = files.index(backup_file)
    return idx, count


def get_backup_version_info(core_name, workbox_id, versionType, backup_file=None):
    """For the given core_name and workbox_id, find the filename based on versionType,
    potentially relative to backup_file . Include the (one-based) index filename is
    within that workbox's backup files, plus the total count of backup files.

    Args:
        core_name (str): The current core_name
        workbox_id (str): The current workbox_id
        versionType (VersionType): The VersionType (ie First, Previous, Next, Last)
        backup_file (None, optional): The currently loaded backup file.

    Returns:
        filepath, display_idx, count (str, int, int): The found filepath, it's
            (one-based) index within backup files, but count of backup files.
    """
    files = get_file_group(core_name, workbox_id)
    if not files:
        return ("", "", 0)
    count = len(files)

    idx = len(files) - 1
    if versionType == VersionTypes.First:
        idx = 0
    elif versionType == VersionTypes.Last:
        idx = len(files) - 1
    else:
        idx, count = get_backup_file_index_and_count(
            core_name, workbox_id, backup_file, files=files
        )
        if idx is not None:
            if versionType == VersionTypes.TwoBeforeLast:
                idx -= 2
                idx = max(idx, 0)
            elif versionType == VersionTypes.Previous:
                idx -= 1
                idx = max(idx, 0)
            elif versionType == VersionTypes.Next:
                idx += 1
                idx = min(idx, count - 1)

    filepath = str(files[idx])
    display_idx = idx + 1
    return filepath, display_idx, count


def get_prefs_updates():
    """Get any defined updates to prefs args / values

    Returns:
        updates (dict): The dict of defined updates
    """
    updates = {}
    path = resourcePath("pref_updates/pref_updates.json")
    try:
        updates = utils.Json(path).load()
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        pass
    return updates


def update_pref_args(core_name, pref_dict, old_name, update_data):
    """Update an individual pref name and/or value.

    Args:
        core_name (str): The current core_name
        pref_dict (dict): The pref to update
        old_name (str): Original pref name, which may be updated
        update_data (str): Dict to define ways to update the values, which
        currently only supports str.replace.
    """
    workbox_dir = Path(get_prefs_dir(core_name=core_name, create=True))

    if old_name == "tempfile":
        orig_pref = pref_dict.get(old_name)
    else:
        orig_pref = pref_dict.pop(old_name)
    pref = orig_pref[:] if isinstance(orig_pref, list) else orig_pref

    if isinstance(pref, str):
        replacements = update_data.get("replace", [])
        for replacement in replacements:
            pref = pref.replace(*replacement)

    existing_backup_file = pref_dict.get("backup_file", None)
    if not existing_backup_file and old_name == "tempfile":
        newfilepath = create_stamped_path(core_name, pref)
        orig_filepath = workbox_dir / orig_pref
        if orig_filepath.is_file():
            orig_filepath = str(orig_filepath)

            if not Path(newfilepath).is_file():
                shutil.copy(orig_filepath, newfilepath)
            newfilepath = str(Path(newfilepath).relative_to(workbox_dir))

            pref_dict.update({"backup_file": newfilepath})

    pref_name = old_name
    if isinstance(update_data, dict):
        pref_name = update_data.get("new_name", old_name)

    pref_dict.update({pref_name: pref})


def update_prefs_args(core_name, prefs_dict, prefs_updates):
    """Update all the PrEditor prefs, as defined in prefs_updates

    Args:
        core_name (str): The current core_name
        prefs_dict (dict): The PrEditor prefs to update
        prefs_updates (dict): The update definition dict

    Returns:
        prefs_dict (dict): The updated dict
    """

    # Check if we have already updated to this prefs_update version
    update_version = prefs_updates.get("prefs_version", 1.0)

    for old_name, data in prefs_updates.items():
        if old_name not in prefs_dict:
            continue

        if old_name == "workbox_prefs":
            for sub_old_name, sub_data in prefs_updates["workbox_prefs"].items():
                for group_dict in prefs_dict["workbox_prefs"]["groups"]:
                    for tab_dict in group_dict["tabs"]:
                        if sub_old_name not in tab_dict:
                            continue
                        update_pref_args(core_name, tab_dict, sub_old_name, sub_data)
        else:
            update_pref_args(core_name, prefs_dict, old_name, data)

    prefs_dict["prefs_version"] = update_version

    return prefs_dict
