import os
import glob
import blurdev
import getpass


def getPrefs(limit=None, allUsers=False):
    """ Gather the prefs arguments needed to find old style treegrunt favorites
    """
    globString = blurdev.prefs.Preference.path(coreName='*')
    if allUsers:
        globString = globString.replace(getpass.getuser(), '*')

    rootPath = os.path.dirname(globString)
    globString = os.path.join(globString, 'treegrunt', '*_favorites.pref')
    cores = {}
    for filename in glob.glob(globString):
        filename = os.path.normpath(filename)
        relativePath = filename.replace(rootPath + os.path.sep, '')
        coreName = relativePath.split(os.path.sep)[0].replace('app_', '')
        path = os.path.splitext(relativePath.split(os.path.sep, 1)[1])[0]
        if limit and coreName != limit:
            continue
        cores.setdefault(coreName, []).append(path)
    return cores


def getFavorites(name, coreName, favorites):
    """ Extract favorites from a prefs file.
    """
    prefs = blurdev.prefs.find(name, coreName=coreName, reload=True)
    children = prefs.root().children()
    for child in children:
        if child.nodeName == 'tool':
            favorites.add(child.attribute('id'))


def mergePrefs(cores):
    """ Combine all the old per treegrunt environment favorites to a single
    favorites file.
    """
    for coreName in cores:
        # No need to re-add these favorites
        existing = set()
        getFavorites('treegrunt/favorites', coreName, existing)
        favorites = set()
        getFavorites('treegrunt/favorites', coreName, favorites)
        for pref in cores[coreName]:
            getFavorites(pref, coreName, favorites)
        # Note: this will make duplicate entries, but this will get fixed when the prefs
        # are saved normally
        prefs = blurdev.prefs.find(
            'treegrunt/favorites', coreName=coreName, reload=True
        )
        root = prefs.root()
        print('Updating: {}'.format(prefs.filename()))
        for favorite in favorites:
            if favorite not in existing:
                print('\tAdding: {}'.format(favorite))
                node = root.addNode('tool')
                node.setAttribute('id', favorite)
        prefs.save()


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
