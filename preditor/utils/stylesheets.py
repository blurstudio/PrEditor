from __future__ import absolute_import

import glob
import os


def read_stylesheet(stylesheet='', path=None):
    """Returns the contents of the requested stylesheet.

    Args:

        stylesheet (str): the name of the stylesheet. Attempt to load stylesheet.css
            shipped with preditor. Ignored if path is provided.

        path (str): Return the contents of this file path.

    Returns:
        str: The contents of stylesheet or blank if stylesheet was not found.
        valid: A stylesheet was found and loaded.
    """
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'resource',
            'stylesheet',
            '{}.css'.format(stylesheet),
        )
    if os.path.isfile(path):
        with open(path) as f:
            return f.read(), True
    return '', False


def stylesheets(subFolder=None):
    """Returns a list of installed stylesheet names.

    Args:
        subFolder (str or None, optional): Use this to access sub-folders of
            the stylesheet resource directory.

    Returns:
        list: A list .css file paths in the target directory.
    """
    components = [
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'resource',
        'stylesheet',
    ]
    if subFolder is not None:
        components.append(subFolder)
    cssdir = os.path.join(*components)
    cssfiles = sorted(glob.glob(os.path.join(cssdir, '*.css')))
    # Only return the filename without the .css extension
    return [os.path.splitext(os.path.basename(fp))[0] for fp in cssfiles]
