##
# 	\namespace	blurdev.ide.addons.svn
#
# 	\remarks	Creates connections to the IDE editor for SVN
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

# required python module for the SVN interface
from blurdev.ide.ideaddon import IdeAddon
from blurdev.ide.ideregistry import RegistryType

STATUS_ORDER = {
    'ignored': 5,
    'unversioned': 4,
    'normal': 3,
    'added': 2,
    'modified': 1,
    'conflicted': 0,
}


class SvnAddon(IdeAddon):
    def activate(self, ide):
        """
            \remarks	registers the SvnFileMenu as the default file menu for the IDE editor
            \param		ide		<blurdev.ide.IdeEditor>
            \return		<bool> success
        """
        # make sure that we can import the pysvn module
        import pysvn

        # connect the filemenu class
        from blurdev.ide.addons.svn.svnfilemenu import SvnFileMenu

        ide.setFileMenuClass(SvnFileMenu)

        # connect the svn overlay lookup method
        ide.registry().register(RegistryType.Overlay, '.*', self.filepathOverlay)

        # connect the settings recorded signal
        from blurdev.ide.addons.svn import svnconfig

        ide.settingsRecorded.connect(svnconfig.recordSettings)

        # set the colors based on the ide preferences
        from blurdev.ide.addons.svn import svnconfig

        configSet = ide.globalConfigSet()
        scheme = configSet.section('Editor::Scheme')

        # set the default svn environment variables
        from blurdev import settings

        settings.startup_environ.setdefault('SVN_APP_COMPARE', 'kdiff3')
        settings.startup_environ.setdefault(
            'SVN_CMD_COMPARE',
            'svn diff --diff-cmd $SVN_APP_COMPARE -r %(revision)s %(filepath)s',
        )

        svnconfig.ACTION_COLORS['Add'] = scheme.value('document_color_string')
        svnconfig.ACTION_COLORS['Added'] = scheme.value('document_color_string')
        svnconfig.ACTION_COLORS['Conflict'] = scheme.value('document_color_number')
        svnconfig.ACTION_COLORS['External'] = scheme.value('document_color_text')
        svnconfig.ACTION_COLORS['Replace'] = scheme.value('document_color_text')
        svnconfig.ACTION_COLORS['Replaced'] = scheme.value('document_color_text')
        svnconfig.ACTION_COLORS['Modified'] = scheme.value('document_color_keyword')
        svnconfig.ACTION_COLORS['Update'] = scheme.value('document_color_keyword')
        svnconfig.ACTION_COLORS['Revert'] = scheme.value('document_color_keyword')
        svnconfig.ACTION_COLORS['Delete'] = scheme.value('document_color_number')
        svnconfig.ACTION_COLORS['Deleted'] = scheme.value('document_color_number')
        svnconfig.ACTION_COLORS['Error'] = scheme.value('document_color_number')
        svnconfig.ACTION_COLORS['COmmand'] = scheme.value('document_color_text')
        svnconfig.ACTION_COLORS['Completed'] = scheme.value('document_color_comment')

        svnconfig.restoreSettings()

        return True

    def filepathOverlay(self, filepath):
        import pysvn

        client = pysvn.Client()

        # make sure we have a client svn area
        try:
            status = client.status(filepath, recurse=False, ignore_externals=True)
        except:
            return ''

        # collect the state for the status
        last_status = 'unversioned'
        last_order = 50000
        for entry in status:
            tstatus = str(entry.text_status)
            order = STATUS_ORDER.get(tstatus, -1)

            # skip over ignored statuses
            if order == -1:
                continue

            # update the status
            if order < last_order:
                last_order = order
                last_status = tstatus

        return OVERLAYS.get(last_status, '')

    def deactivate(self, ide):
        """
            \remarks	unregisters the SvnFileMenu as the default file menu for the IDE Editor
            \param		ide		<blurdev.ide.IdeEditor>
            \return		<bool> success
        """
        # disconnect the filemenu class
        from blurdev.ide.idefilemenu import IdeFileMenu

        ide.setFileMenuClass(IdeFileMenu)

        # disconnect the svn overlay lookup method
        ide.registry().unregister(RegistryType.Overlay, '*', self.findOverlay)

        # disconnect the settings recorded method
        from blurdev.ide.addons.svn import svnconfig

        ide.settingsRecorded.disconnect(svnconfig.recordSettings)

        return True


def login(realm, username, may_save):
    from blurdev.ide.addons.svn.svnlogindialog import SvnLoginDialog

    return SvnLoginDialog.login(realm, username, may_save)


def resource(relpath):
    import os.path

    return os.path.join(os.path.dirname(__file__), relpath)


# register the IdeAddon to the IDE system
IdeAddon.register('SVN Support', SvnAddon)

# define global resources
OVERLAYS = {}
OVERLAYS['modified'] = resource('img/filesystem_modified.png')
OVERLAYS['normal'] = resource('img/filesystem_normal.png')
OVERLAYS['added'] = resource('img/filesystem_add.png')
OVERLAYS['conflicted'] = resource('img/filesystem_conflict.png')
OVERLAYS['unversioned'] = resource('img/filesystem_unversioned.png')
OVERLAYS['ignored'] = resource('img/filesystem_ignored.png')
