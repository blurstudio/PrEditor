"""
Version module to track the version information for blurdev
"""

import os
import pillar.version

ver = pillar.version.Version(os.path.dirname(os.path.abspath(__file__)), 'blur-blurdev')


def major():
    return ver.major()


def minor():
    return ver.minor()


def current(asDict=False):
    return ver.current(asDict)


def currentBuild():
    return ver.current_build()


def fromString(version, asDict=False):
    return ver.fromString(version, asDict)


def toString(version=None, prepend_v=True):
    return ver.toString(version=version, prepend_v=prepend_v)


def versionString(major, minor, build, prepend_v=True):
    return ver.versionString(major=major, minor=minor, build=build, prepend_v=prepend_v)


def url(major=None, minor=None, currentBuild=None):
    return ver.url(major, minor, currentBuild)
