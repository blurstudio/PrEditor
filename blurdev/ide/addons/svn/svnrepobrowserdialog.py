##
# 	\namespace	blurdev.ide.addons.svn.svnrepobrowserdialog
#
# 	\remarks	Creates a dialog for browing the SVN repository
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/26/11
#

import os.path
import datetime
import pysvn

from PyQt4.QtCore import Qt, QVariant
from PyQt4.QtGui import QTreeWidgetItem, QIcon, QApplication

import blurdev
from blurdev.gui import Dialog

from blurdev.ide.addons.svn import svnconfig

client = pysvn.Client()


class SvnFileItem(QTreeWidgetItem):
    def __init__(self, info):
        # extract the information
        filename = os.path.basename(info.name)
        extension = os.path.splitext(filename)[1]
        revision = str(info.created_rev.number)
        author = str(info.last_author)
        size = str(info.size)
        date = datetime.datetime.fromtimestamp(info.time).strftime('%Y-%m-%d %H:%M:%S')
        lock = 'False'

        # initialize the item
        QTreeWidgetItem.__init__(
            self, [filename, extension, revision, author, size, date, lock]
        )
        self._info = info

        self.setIcon(0, QIcon(blurdev.resourcePath('img/file.png')))

    def info(self):
        return self._info


class SvnUrlItem(QTreeWidgetItem):
    def __init__(self, url):
        QTreeWidgetItem.__init__(self, [url.split('/')[-1]])

        # create the list information
        self.setIcon(0, QIcon(blurdev.resourcePath('img/folder.png')))

        # create custom properties
        self._info = None
        self._url = url
        self._files = []

        # update the look of the item
        self._loaded = False
        self.setChildIndicatorPolicy(self.ShowIndicator)

    def findChild(self, name):
        for i in range(self.childCount()):
            child = self.child(i)
            if child.text(0) == name:
                return child
        return None

    def info(self):
        if not self._info:
            name, info = client.info2(self._url)[0]
            self._info = info

        return self._info

    def navigateTo(self, url):
        # mark selected if the urls match
        if self._url == url:
            self.treeWidget().setCurrentItem(self)
            return

        # stop navigating
        if not self._url in url:
            return

        # load the children
        self.load()
        self.setExpanded(True)

        # lookup the next child
        name = url.replace(self._url, '').strip('/').split('/')[0]
        child = self.findChild(name)
        if child:
            child.navigateTo(url)

    def reload(self):
        if self._loaded:
            # clear the children
            while self.childCount():
                self.takeChild(0)

            # clear the files
            self._files = []
            self._loaded = False

        self.load()

    def load(self):
        if self._loaded:
            return

        # reset the indicator policy
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._loaded = True

        self.setChildIndicatorPolicy(self.DontShowIndicatorWhenChildless)
        for entry in client.ls(self._url, recurse=False):
            if entry.kind != pysvn.node_kind.file:
                self.addChild(SvnUrlItem(entry.name))
            else:
                self._files.append(entry)

        QApplication.restoreOverrideCursor()

    def files(self):
        return self._files

    def url(self):
        return self._url


class SvnRepoBrowserDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self.uiUrlTXT.setText(svnconfig.CURRENT_URL)

        header = self.uiFilesTREE.header()
        for i in range(self.uiFilesTREE.columnCount() - 1):
            header.setResizeMode(i, header.ResizeToContents)

        # create connections
        self.uiUrlTXT.returnPressed.connect(self.reset)

        self.uiBrowserTREE.itemSelectionChanged.connect(self.showItem)
        self.uiBrowserTREE.itemExpanded.connect(self.loadItem)

    def closeEvent(self, event):
        super(SvnRepoBrowserDialog, self).closeEvent(event)
        svnconfig.CURRENT_URL = self.url()

    def loadItem(self, item):
        item.load()

    def reset(self):
        try:
            baseurl = client.root_url_from_path(self.url())
        except:
            baseurl = ''

        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.uiBrowserTREE.setUpdatesEnabled(False)
        self.uiBrowserTREE.blockSignals(True)

        self.uiBrowserTREE.clear()

        if baseurl:
            item = SvnUrlItem(baseurl)
            item.setText(0, baseurl)
            self.uiBrowserTREE.addTopLevelItem(item)
            item.navigateTo(self.url())
            self.showItem()

        self.uiBrowserTREE.setUpdatesEnabled(True)
        self.uiBrowserTREE.blockSignals(False)

        QApplication.restoreOverrideCursor()

    def showItem(self):
        item = self.uiBrowserTREE.currentItem()
        if not item:
            return

        self.uiUrlTXT.setText(item.url())

        self.uiFilesTREE.setUpdatesEnabled(False)
        self.uiFilesTREE.blockSignals(True)

        self.uiFilesTREE.clear()
        if item:
            item.load()
            for file in item.files():
                self.uiFilesTREE.addTopLevelItem(SvnFileItem(file))

        self.uiFilesTREE.setUpdatesEnabled(True)
        self.uiFilesTREE.blockSignals(False)

    def setUrl(self, url):
        self.uiUrlTXT.setText(url)

    def url(self):
        return str(self.uiUrlTXT.text())

    # define static methods
    @staticmethod
    def getUrl(url=''):
        import blurdev

        dlg = SvnRepoBrowserDialog(blurdev.core.rootWindow())

        if url:
            dlg.setUrl(url)

        dlg.reset()
        if dlg.exec_():
            svnconfig.CURRENT_URL = dlg.url()
            return str(dlg.url())
        return ''

    @staticmethod
    def browse(url=''):
        import blurdev

        dlg = SvnRepoBrowserDialog(blurdev.core.rootWindow())

        if url:
            dlg.setUrl(url)

        dlg.reset()
        dlg.uiOkBTN.setVisible(False)
        dlg.uiCancelBTN.setText('Close')
        dlg.show()
