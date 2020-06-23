##
# 	\namespace	blurdev.ide.addons.svn.settings
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

from Qt.QtGui import QColor

# global settings
CURRENT_URL = ''
RECENT_MESSAGES = []

# parameters
ACTION_COLORS = {
    'Add': QColor('darkOrange'),
    'Added': QColor('darkOrange'),
    'Conflict': QColor('red'),
    'External': QColor('gray'),
    'Replace': QColor('darkGray'),
    'Replaced': QColor('darkGray'),
    'Modified': QColor('blue'),
    'Update': QColor('blue'),
    'Revert': QColor('blue'),
    'Delete': QColor('red'),
    'Deleted': QColor('red'),
    'Error': QColor('red'),
    'Command': QColor('gray'),
    'Completed': QColor('darkGreen'),
    'default': None,
}

STATUS_DEFAULT = {
    'commit_visible': False,
    'commit_checked': False,
    'commit_error': False,
    'foreground': 'default',
    'background': 'default',
    'sort_order': 5000,
}

STATUS_DATA = {
    'added': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': 'Added',
        'sort_order': 1,
    },
    'conflicted': {
        'commit_error': True,
        'commit_visible': True,
        'foreground': 'Conflict',
        'sort_order': 0,
    },
    'deleted': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': 'Deleted',
        'sort_order': 1,
    },
    'modified': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': 'Modified',
        'sort_order': 1,
    },
    'replaced': {'commit_visible': True, 'commit_checked': True, 'sort_order': 1,},
    'unversioned': {'commit_visible': True, 'commit_checked': False,},
}


def recordMessage(msg):
    global RECENT_MESSAGES

    # if the user re-selects, just move it up
    if msg in RECENT_MESSAGES:
        RECENT_MESSAGES.remove(msg)

    RECENT_MESSAGES.insert(0, msg)
    RECENT_MESSAGES = RECENT_MESSAGES[:20]


def statusData(status):
    output = {}
    output.update(STATUS_DEFAULT)
    output.update(STATUS_DATA.get(str(status), {}))
    return output


def sortStatus(a, b):
    adat = statusData(a.text_status)
    bdat = statusData(b.text_status)

    cmp = lambda x, y: (x > y) - (x < y)
    # sort by the order of the statuses
    if adat['sort_order'] != bdat['sort_order']:
        return cmp(adat['sort_order'], bdat['sort_order'])

    # sort by their name
    return cmp(a.path, b.path)


def recordSettings():
    from blurdev import prefs

    pref = prefs.find('addons/svn')

    pref.recordProperty('current_url', CURRENT_URL)
    pref.recordProperty('recent_messages', RECENT_MESSAGES)
    pref.save()


def restoreSettings():
    from blurdev import prefs

    pref = prefs.find('addons/svn')

    global CURRENT_URL
    CURRENT_URL = pref.restoreProperty('current_url', '')

    global RECENT_MESSAGES
    RECENT_MESSAGES = pref.restoreProperty('recent_messages', [])
