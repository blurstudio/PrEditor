"""A collection of utils for working with files."""

import os
import sys
import shutil


def listfiles(path):
    """Similar to os.listdir, but returns only files."""
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]


def listdirs(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
