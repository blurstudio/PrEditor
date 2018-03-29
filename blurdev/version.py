""" Version module to track the version information for blurdev
"""

import os
import re

_major = 2  # User defined major version
_minor = 1  # User defined minor version

# Load build version from file
_currentBuild = 0
filename = os.path.split(__file__)[0] + '/build.txt'
if os.path.exists(filename):
    f = open(filename, 'r')
    _currentBuild = int(f.read())
    f.close()


def major():
    return _major


def minor():
    return _minor


def current(asDict=False):
    """ Returns the current version as tuple or dict.

    Args:
        asDict (bool, optional): Return the value as a dict. If False(the default)
            a tuple will be returned.

    Returns:
        tuple or dict: Returns a tuple containing 3 ints (major, minor, build).
            if asDict is True, a dict is returned.
    """
    if asDict:
        return dict(major=major(), minor=minor(), build=currentBuild())
    return (major(), minor(), currentBuild())


def currentBuild():
    return _currentBuild


def fromString(version, asDict=False):
    """ Converts a string into a tuple or dict of version info.

    Args:
        version (str): A valid string version. Example: "v01.1.123" or "1.1.123"
        asDict (bool, optional): Return the value as a dict. If False(the default)
            a tuple will be returned.

    Returns:
        tuple or dict: Returns a tuple containing 3 ints (major, minor, build).
            if asDict is True, a dict is returned.

    Raises:
        ValueError: A invalid version string was provided.
    """
    match = re.match(r'[vV]?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<build>\d+)', version)
    if match:
        # Convert to int values
        ret = match.groupdict()
        ret['major'] = int(ret['major'])
        ret['minor'] = int(ret['minor'])
        ret['build'] = int(ret['build'])
        if asDict:
            return ret
        return (ret['major'], ret['minor'], ret['build'])
    raise ValueError('Invalid version string: {}'.format(version))


def toString(version=None):
    # return the current version information for this system
    if version is None:
        vstr = versionString(major(), minor(), currentBuild())
        return vstr

    # return the version string for a float
    elif isinstance(version, float):
        maj = int(version)
        min = round((version % 1) * 100)
        build = 0
        return versionString(maj, min, build)


def versionString(major, minor, build):
    return 'v%i.%02i.%i' % (major, minor, build)
