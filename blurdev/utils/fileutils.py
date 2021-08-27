"""A collection of utils for working with files."""

from __future__ import absolute_import
import os
import shutil
import fnmatch
import threading


def listfiles(path):
    """Similar to os.listdir, but returns only files."""
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def listdirs(path):
    """Similar to os.listdir, but returns only dirs."""
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]


def rglob(treeroot, pattern):
    """Recursive glob an entire directory tree."""
    results = []
    for root, _, files in os.walk(treeroot):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend([os.path.join(root, f) for f in goodfiles])
    return results


def makedirs(path):
    """Similar to os.makedirs, but surrounded in a check to make sure the
    path doesn't exist first.

    """
    if not os.path.exists(path):
        os.makedirs(path)


def threadedCopy(filepaths):
    """
    This function will copy a set of files in a separate thread.

    filepaths is a list of (from_path, to_path) pairs::

        [('C:/src/path.txt', 'C:/destination/path.txt'),
        ('C:/src/path1.txt', 'C:/destination/path1.txt'),
        ('C:/src/path2.txt', 'C:/destination/path2.txt')]

    Uses the :class:`CopyThread` class.

    """
    CopyThread(filepaths).start()


class CopyThread(threading.Thread):
    def __init__(self, filepaths):
        super(CopyThread, self).__init__()
        self.filepaths = filepaths

    def run(self):
        for paths in self.filepaths:
            src, dst = paths
            shutil.copyfile(src, dst)
