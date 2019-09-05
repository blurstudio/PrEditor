import os
import glob
import blurdev
import getpass


def getPrefs(limit=None, allUsers=False):
    """ Gather the prefs arguments needed to find old style treegrunt favorites
    """
    roots = [os.path.dirname(blurdev.prefs.Preference.path())]
    if allUsers:
        # Handle the migration user folders like magma.0000, etc
        # user_folder = os.path.split(os.environ['USERPROFILE'])[-1]
        # globString = roots[0].replace(user_folder, '*')
        globString = r'C:\Users\*\AppData\Roaming\blur\userprefs'
        roots = list(set([x for x in set(glob.glob(globString))]))

    all_prefs = {}
    for root in roots:
        globString = os.path.join(root, 'app_*', 'treegrunt', '*_favorites.pref')
        for filename in glob.glob(globString):
            relativePath = filename.replace(root + os.path.sep, '')
            coreName = relativePath.split(os.path.sep)[0].replace('app_', '')
            path = os.path.splitext(relativePath.split(os.path.sep, 1)[1])[0]
            if limit and coreName != limit:
                continue
            all_prefs.setdefault(root, {}).setdefault(coreName, []).append(path)
    return all_prefs


def getFavorites(path, root, coreName, favorites):
    """ Extract favorites from a prefs file.
    """
    prefs = findPref(path, root, coreName)
    children = prefs.root().children()
    for child in children:
        if child.nodeName == 'tool':
            favorites.add(child.attribute('id'))


def mergePrefs(all_prefs):
    """ Combine all the old per treegrunt environment favorites to a single
    favorites file.
    """
    for root in all_prefs:
        cores = all_prefs[root]
        txt = '# PROCESSING: {}'.format(root)
        print(txt)
        print('#' * len(txt))
        for coreName in cores:
            # No need to re-add these favorites
            existing = set()
            getFavorites('treegrunt/favorites', root, coreName, existing)
            favorites = set()
            getFavorites('treegrunt/favorites', root, coreName, favorites)
            for pref in cores[coreName]:
                getFavorites(pref, root, coreName, favorites)
            # Note: this will make duplicate entries, but this will get fixed when the prefs
            # are saved normally
            prefs = findPref(r'treegrunt\favorites', root, coreName)
            pref_root = prefs.root()
            changes = []
            for favorite in favorites:
                if favorite not in existing:
                    changes.append('    Adding: {}'.format(favorite))
                    node = pref_root.addNode('tool')
                    node.setAttribute('id', favorite)
            if changes:
                print('Updating: {}'.format(prefs.filename()))
                print('\n'.join(changes))
                prefs.save()


def findPref(name, root_path, coreName):
    """ Get a Preference object for any user given its root_path
    """
    key = str(name).replace(' ', '-').lower()
    filename = os.path.join(root_path, 'app_{}'.format(coreName), '%s.pref' % key)
    # create a new preference record
    pref = blurdev.prefs.Preference()
    pref.setCoreName(coreName)
    # look for a default preference file
    success = False
    pref._filename = filename
    if os.path.exists(filename):
        success = pref.load(filename)
    if not success:
        # create default information
        root = pref.addNode('preferences')
        root.setAttribute('name', name)
        root.setAttribute('version', 1.0)
        root.setAttribute('ui', '')
    pref.setName(key)
    return pref


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='Add any favorites from any old per treegrunt environment '
        'favorites to a single shared favorites for the current user.',
    )
    parser.add_argument(
        'limit',
        default=None,
        nargs='?',
        help='If specified, limit to just this core name. Otherwise update all '
        'all of them.',
    )
    parser.add_argument(
        '-a',
        '--all-users',
        action='store_true',
        help='Update the prefs of all users, not just the current one.',
    )
    args = parser.parse_args()
    prefs = getPrefs(args.limit, allUsers=args.all_users)
    mergePrefs(prefs)
    print('Finished merging prefs')
