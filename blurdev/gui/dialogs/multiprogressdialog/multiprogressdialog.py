##
# 	\namespace	python.blurdev.gui.dialogs.multiprogressdialog
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		03/14/11
#

from PyQt4.QtCore import pyqtSignal
from blurdev.gui import Dialog


class MultiProgressDialog(Dialog):
    closed = pyqtSignal()

    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        self._errored = False

        # create the columns
        self.uiProgressTREE.setColumnCount(2)
        header = self.uiProgressTREE.header()
        header.setResizeMode(0, header.Stretch)
        header.setResizeMode(1, header.ResizeToContents)

        # create connections
        self.uiProgressTREE.currentItemChanged.connect(self.updateOptions)
        self.uiDetailsCHK.toggled.connect(self.adjustSize)
        self.uiDialogBTNS.accepted.connect(self.close)
        self.uiDialogBTNS.rejected.connect(
            self.cancel
        )  # assumes there is a uiDialogBTNS in the ui file

    def addSection(self, name, count=100, value=-1, allowsCancel=False):
        self.uiProgressTREE.blockSignals(True)
        self.uiProgressTREE.setUpdatesEnabled(False)

        from blurdev.gui.dialogs.multiprogressdialog import ProgressSection

        section = ProgressSection(
            name, count=count, value=value, allowsCancel=allowsCancel
        )
        self.uiProgressTREE.addTopLevelItem(section)

        self.uiProgressTREE.blockSignals(False)
        self.uiProgressTREE.setUpdatesEnabled(True)

        self.update()

        return section

    def cancel(self):
        item = self.uiProgressTREE.currentItem()
        if item:
            item.cancel()

    def clear(self):
        self.uiProgressTREE.blockSignals(True)
        self.uiProgressTREE.setUpdatesEnabled(False)

        self.uiProgressTREE.clear()
        self._errored = False

        self.uiProgressTREE.blockSignals(False)
        self.uiProgressTREE.setUpdatesEnabled(True)

    def closeEvent(self, event):
        Dialog.closeEvent(self, event)
        self.closed.emit()

    def errored(self):
        return self._errored

    def finish(self):
        for i in range(self.uiProgressTREE.topLevelItemCount()):
            item = self.uiProgressTREE.topLevelItem(i)
            item._value = item._count - 1

        self.update()

    def reset(self, items):
        self.uiProgressTREE.blockSignals(True)
        self.uiProgressTREE.setUpdatesEnabled(False)

        self.uiProgressTREE.clear()
        for item in items:
            self.uiProgressTREE.addTopLevelItem(item)

        self.uiMainPBAR.setValue(0)
        self.uiItemPBAR.setValue(0)

        self.uiProgressTREE.blockSignals(False)
        self.uiProgressTREE.setUpdatesEnabled(True)

    def section(self, name):
        for i in range(self.uiProgressTREE.topLevelItemCount()):
            item = self.uiProgressTREE.topLevelItem(i)
            if item.text(0) == name:
                return item
        return None

    def show(self):
        Dialog.show(self)

        from PyQt4.QtGui import QApplication

        QApplication.processEvents()

    def update(self):
        # we need to force the events to process to check if the user pressed the cancel button since this is not multi-threaded
        from PyQt4.QtGui import QApplication

        QApplication.processEvents()

        # update the progress
        tree = self.uiProgressTREE

        citem = tree.currentItem()
        count = tree.topLevelItemCount()
        completeCount = 0.0
        secondaryPerc = 0
        self._errored = False
        self.uiDialogBTNS.setStandardButtons(self.uiDialogBTNS.Cancel)

        for i in range(count):
            item = tree.topLevelItem(i)

            # if the item has accepted a user cancel, stop the progress dialog
            if item.cancelAccepted():
                self.close()
                break

            # convert an errored item to a message box style system
            elif item.errored():
                self.uiDialogBTNS.setStandardButtons(self.uiDialogBTNS.Ok)
                self._errored = True

            # calculate overall percent complete for completed items
            if item.completed():
                completeCount += 1
                continue

            # calculate the secondary percentage
            iperc = item.percentComplete()
            completeCount += 1 * iperc

            if item == citem:
                secondaryPerc = 100 * iperc

        if count < 1:
            count = 1

        self.uiMainPBAR.setValue(100 * (completeCount / count))
        self.uiItemPBAR.setValue(secondaryPerc)
        self.updateOptions()

        # close out when all items are finished
        if self.uiMainPBAR.value() == 100:
            self.close()

    def updateOptions(self):
        item = self.uiProgressTREE.currentItem()
        if item:
            self.uiDialogBTNS.setEnabled(item.allowsCancel() or self.errored())
        else:
            self.uiDialogBTNS.setEnabled(self.errored())
