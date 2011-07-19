##
# 	\namespace	blurdev.ide.addons.svn.settings
#
# 	\remarks	[desc::commented]
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

from PyQt4.QtGui import QColor

# global settings
CURRENT_URL = ''

# parameters
ACTION_COLORS = {
    'Add': QColor('darkOrange'),
    'Added': QColor('darkOrange'),
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
}

STATUS_DEFAULT = {
    'commit_visible': False,
    'commit_checked': False,
    'commit_error': False,
    'foreground': None,
    'background': None,
    'sort_order': 5000,
}

STATUS_DATA = {
    'added': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': ACTION_COLORS['Added'],
        'sort_order': 1,
    },
    'conflicted': {
        'commit_error': True,
        'foreground': QColor('darkRed'),
        'sort_order': 0,
    },
    'deleted': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': ACTION_COLORS['Deleted'],
        'sort_order': 1,
    },
    'modified': {
        'commit_visible': True,
        'commit_checked': True,
        'foreground': ACTION_COLORS['Modified'],
        'sort_order': 1,
    },
    'replaced': {'commit_visible': True, 'commit_checked': True, 'sort_order': 1,},
    'unversioned': {'commit_visible': True, 'commit_checked': False,},
}


def statusData(status):
    output = {}
    output.update(STATUS_DEFAULT)
    output.update(STATUS_DATA.get(str(status), {}))
    return output


def sortStatus(a, b):
    adat = statusData(a.text_status)
    bdat = statusData(b.text_status)

    # sort by the order of the statuses
    if adat['sort_order'] != bdat['sort_order']:
        return cmp(adat['sort_order'], bdat['sort_order'])

    # sort by their name
    return cmp(a.path, b.path)


def recordSettings():
    from blurdev import prefs

    pref = prefs.find('addons/svn')

    pref.recordProperty('current_url', CURRENT_URL)
    pref.save()


def restoreSettings():
    from blurdev import prefs

    pref = prefs.find('addons/svn')

    global CURRENT_URL
    CURRENT_URL = pref.restoreProperty('current_url', '')
