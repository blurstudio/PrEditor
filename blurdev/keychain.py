"""
Used to securely store sensitive strings like api keys. All sensitive data is
stored outside of svn history in xml files and retreived using generic keys.

"""

import os
import os.path
from collections import OrderedDict
from builtins import str as text

import blurdev

# =============================================================================
# FUNCTIONS
# =============================================================================


def getKey(name, default=None, path=None):
    """
    Returns the value of the key with the given name from the given keychain
    file.  If no keychain path is given, the default keychain path is used.
    If no key with the given name is found, it will raise a KeyError, unless
    a default is provided, in which case the default will be returned.
    """
    keys = getKeys(path)
    value = keys.get(name, default)
    if value is None:
        msg = 'Unable to find the key "{name}" in the provided keychain. "{keychain}"'
        raise KeyError(
            msg.format(
                name=name, keychain=path
            )
        )
    return value


# =============================================================================


def setKey(name, value, path=None):
    """
    Uses the provided name and value to add or update a key in the given
    keychain file.  If no path is provided, the default keychain file is
    updated.
    """
    if path:
        # Force this to only accept files with the ext keychain.
        path = '{}.keychain'.format(os.path.splitext(path)[0])
    else:
        path = _getDefaultPath()

    keys = getKeys(path)
    keys[name] = value
    setKeys(keys, path)


# =============================================================================


def getKeys(path=None):
    """
    Accepts a path to a keychain file and returns a dictionary of key: value pairs.
    If no path is provided, the default path will be used.

    """
    if path:
        # Force this to only accept files with the ext keychain.
        path = '{}.keychain'.format(os.path.splitext(path)[0])
        if not os.path.exists(path):
            return dict()
    else:
        path = _getDefaultPath()

    # 3 possible formats, detect which format is being used and parse the file
    # appropriately
    if path.lower().endswith('.json'):
        version = 3
    else:
        from lxml import etree

        tree = etree.parse(path)
        root = tree.getroot()
        version = 1 if any([ekey.tag != 'key' for ekey in root]) else 2

    # <KEY_NAME>KEY_VALUE</KEY_NAME>
    if version == 1:
        keys = OrderedDict()
        for ekey in root:
            keys[ekey.tag] = text(ekey.text)
    elif version == 2:
        keys = OrderedDict()
        # <key name=KEY_NAME value=KEY_VALUE />
        for ekey in root:
            keys[ekey.get('name')] = text(ekey.get('value'))
    elif version == 3:
        # The json structure already mirrors the expected key:value dict.
        import json

        with open(path, 'r') as fh:
            keys = json.load(fh, object_pairs_hook=OrderedDict)
    return keys


# =============================================================================


def setKeys(keys, path, version=3):
    """
    Accepts a dictionary of {key: value} pairs and writes out a keychain file.
    The version specifies the keychain version format to use (1 or 2).

    """
    if version == 3:
        import json

        with open(path, 'w') as fh:
            json.dump(keys, fh, indent=4)
    else:
        from lxml import etree

        # Order keys alphabetically so that the keychain file is sorted.
        keys = OrderedDict([(key, keys[key]) for key in sorted(keys.keys())])

        # <KEY_NAME>KEY_VALUE</KEY_NAME>
        if version == 1:
            root = etree.Element('keychain')
            for name, value in keys.items():
                ekey = etree.SubElement(root, name)
                ekey.text = value

        # <key name=KEY_NAME value=KEY_VALUE />
        elif version == 2:
            root = etree.Element('keychain')
            for name, value in keys.items():
                ekey = etree.SubElement(root, 'key', {'name': name, 'value': value})

        else:
            raise ValueError('Invalid version (must be 1 or 2)')

        xml_str = etree.tostring(
            root, encoding='utf-8', xml_declaration=True, pretty_print=True
        )
        with open(path, 'w') as f:
            f.write(xml_str)


# =============================================================================


def convertToV2(src, dest):
    if os.path.exists(src):
        keys = getKeys(src)
        setKeys(keys, dest, version=2)


# =============================================================================


def _getDefaultPath():
    path = None
    env = blurdev.activeEnvironment()
    if hasattr(env, 'keychain'):
        path = env.keychain()
    if not path and os.environ.get('keychain'):
        path = os.environ['keychain']
    if not path:
        if env.isOffline() and env.objectName() != blurdev.tools.TEMPORARY_TOOLS_ENV:
            basepath = blurdev.osystem.expandvars(os.environ['BDEV_PATH_BLUR'])
            path = os.path.normpath(os.path.join(basepath, 'keychain'))
        else:
            path = blurdev.osystem.forOS(
                r'\\source\production\keychain', '/mnt/source/keychain'
            )
    if path:
        return path + '.json'
    else:
        return None


# =============================================================================
