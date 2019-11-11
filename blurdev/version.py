"""
Version module to track the version information for blurdev
"""

import os
import pillar.version
from deprecated import deprecated

ver = pillar.version.Version(os.path.dirname(os.path.abspath(__file__)), 'blur-blurdev')


def major():
    return ver.major()


def minor():
    return ver.minor()


def current(asDict=False):
    return ver.current(asDict)


def currentBuild():
    return ver.current_build()


@deprecated(version='2.24.0', reason='You should use "from_string" instead')
def fromString(version, asDict=False):
    return ver.from_string(version, as_dict=asDict)


def from_string(version, as_dict=False):
    return ver.from_string(version, as_dict=asDict)


@deprecated(version='2.24.0', reason='You should use "to_string" instead')
def toString(version=None, prepend_v=True):
    return ver.to_string(version=version, prepend_v=prepend_v)


def to_string(version=None, prepend_v=True):
    return ver.to_string(version=version, prepend_v=prepend_v)


@deprecated(version='2.24.0', reason='You should use "version_string" instead')
def versionString(major, minor, build, prepend_v=True):
    return ver.version_string(
        major=major, minor=minor, build=build, prepend_v=prepend_v
    )


def version_string(major, minor, build, prepend_v=True):
    return ver.version_string(
        major=major, minor=minor, build=build, prepend_v=prepend_v
    )


def url(major=None, minor=None, current_build=None, currentBuild=None):
    """ Generate a url to documentation.

    Args:
        major (int, optional):
        minor (int, optional):
        current_build (int, optional):
        currentBuild (int, optional): Deprecated, use current_build instead.

    Returns:
        str: The documentation url.
    """
    return ver.url(major, minor, current_build=current_build, currentBuild=currentBuild)
