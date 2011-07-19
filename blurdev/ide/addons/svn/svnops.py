##
# 	\namespace	blurdev.ide.addons.svn.svnops
#
# 	\remarks	shortcut methods to all the actions that use the Qt interface to happen
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		05/17/11
#

import pysvn
import os.path
import blurdev

from PyQt4.QtGui import QFileDialog, QInputDialog, QLineEdit


def add(filepath):
    """
        \remarks	adds the filepath using the SvnAddDialog gui
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()

    # promp the user to select non-versioned files
    emptyMessage = 'There is nothing to add.  All the files and folders are either under version control\nor have been ignored using the svn.ignore property\nor the global ignore configuration setting.'
    from svnfilesdialog import SvnFilesDialog

    filepaths, accepted = SvnFilesDialog.collect(
        ide, filepath, ['unversioned'], title='Add', emptyMessage=emptyMessage
    )

    # if the user selects the files, then add them
    if accepted and filepaths:
        # create the commit thread
        from threads.addthread import AddThread

        thread = AddThread()
        thread.setFilepaths(filepaths)

        # run the commit action
        from svnactiondialog import SvnActionDialog

        SvnActionDialog.start(ide, thread, title='Add')


def branch(filepath):
    url = findUrl(filepath)
    if not url:
        return False

    from svncopydialog import SvnCopyDialog

    SvnCopyDialog.branch(source=url, target=url)


def browse(filepath='', url=''):
    """
        \remarks	allows the user to browse the repository
        \param		url		<str>	url to start from
        \return		<str>		(will be blank if the user does not complete selection)
    """
    if filepath:
        url = findUrl(filepath)

    from svnrepobrowserdialog import SvnRepoBrowserDialog

    SvnRepoBrowserDialog.browse(url)


def checkout(filepath):
    """
        \remarks	checkout a repository to the inputed filepath directory using
                    the SvnCheckoutDialog gui
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()

    from svncheckoutdialog import SvnCheckoutDialog

    SvnCheckoutDialog.checkout(ide, filepath)


def cleanup(filepath):
    """
        \remarks	cleans the filepath at the inputed location using the SvnActionDialog
                    interface to display feedback
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()

    # create the cleanup thread
    from threads.cleanupthread import CleanupThread

    thread = CleanupThread()
    thread.setFilepath(filepath)

    # create the action dialog
    from svnactiondialog import SvnActionDialog

    SvnActionDialog.start(ide, thread, title='Cleanup')


def commit(filepath):
    """
        \remarks	commits the filepath using the SvnCommitDialog gui
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()
    from svncommitdialog import SvnCommitDialog

    SvnCommitDialog.commit(ide, filepath)


def getUrl(url=''):
    """
        \remarks	prompts the user to select a url from the svn repository
        \param		url		<str>	url to start from
        \return		<str>		(will be blank if the user does not complete selection)
    """
    from svnrepobrowserdialog import SvnRepoBrowserDialog

    return SvnRepoBrowserDialog.getUrl(url)


def findUrl(filepath):
    """
        \remarks	returns the url for the inputed filepath
        \param		filepath	<str>
        \return		<str> url || <str> ''
    """
    client = pysvn.Client()

    # check to see if this is already part of svn
    try:
        entry = client.info(filepath)
    except:
        entry = None

    # create options for SVN filepaths
    if entry:
        return entry.url
    return ''


def rename(basepath):
    """
        \remarks	prompts the user for a new name for the inputed base path
        \param		basepath	<str>
        \return		<str>		new path
    """
    ide = blurdev.core.rootWindow()
    basepath = str(basepath)
    # prompt the user for the file rename
    text, accepted = QInputDialog.getText(
        ide,
        'SVN Rename',
        'Enter new name',
        QLineEdit.Normal,
        os.path.normpath(basepath).split(os.path.sep)[-1],
    )
    if accepted:
        splt = os.path.normpath(basepath).split(os.path.sep)
        splt[-1] = str(text)
        newpath = os.path.join(splt)

        # rename the path in svn
        client = pysvn.Client()
        client.move(basepath, newpath)

        return newpath
    return basepath


def revert(filepath):
    """
        \remarks	prompts the user to revert changes using the SvnRevertDialog
                    interface
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()
    # promp the user to select non-versioned files
    emptyMessage = 'There is nothing to revert.  All the files and folders are up-to-date and unmodified.'
    from svnfilesdialog import SvnFilesDialog

    filepaths, accepted = SvnFilesDialog.collect(
        ide, filepath, ['modified'], title='Revert', emptyMessage=emptyMessage
    )

    # if the user selects the files, then add them
    if accepted and filepaths:
        # create the commit thread
        from threads.revertthread import RevertThread

        thread = RevertThread()
        thread.setFilepaths(filepaths)

        # run the commit action
        from svnactiondialog import SvnActionDialog

        SvnActionDialog.start(ide, thread, title='Revert')


def update(filepath):
    """
        \remarks	updates the filepath at the inputed location using the SvnActionDialog
                    interface to display feedback
        \param		filepath	<str>
    """
    ide = blurdev.core.rootWindow()

    # create the update thread
    from threads.updatethread import UpdateThread

    thread = UpdateThread()
    thread.setFilepath(filepath)

    # create the action dialog
    from svnactiondialog import SvnActionDialog

    SvnActionDialog.start(ide, thread, title='Update')
