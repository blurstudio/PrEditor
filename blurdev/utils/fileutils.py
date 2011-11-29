"""A collection of utils for working with files."""

import os
import sys
import shutil
import fnmatch


def listfiles(path):
    """Similar to os.listdir, but returns only files."""
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def listdirs(path):
    """Similar to os.listdir, but returns only dirs."""
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]


def rglob(treeroot, pattern):
    """Recursive glob an entire directory tree."""
    results = []
    for root, dirs, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend([os.path.join(root, f) for f in goodfiles])
    return results
