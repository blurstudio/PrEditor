##
# 	\namespace	blurdev.ide.addons.yaml.yamldialog
#
# 	\remarks
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		05/03/11
#

from blurdev.gui import Dialog


class YamlDialog(Dialog):
    def __init__(self, parent=None):
        Dialog.__init__(self, parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        # define custom properties
        self._document = None

        # set ui icons
        from PyQt4.QtGui import QIcon, QToolButton

        for btn in self.findChildren(QToolButton):
            btn.setAutoRaise(True)
            bname = str(btn.objectName())
            if bname.startswith('uiAdd'):
                btn.setIcon(QIcon(blurdev.resourcePath('img/add.png')))
                try:
                    btn.clicked.connect(
                        getattr(self, bname.replace('uiAdd', 'add').replace('BTN', ''))
                    )
                except:
                    print 'error creating connection for', bname
            elif bname.startswith('uiRemove'):
                btn.setIcon(QIcon(blurdev.resourcePath('img/remove.png')))
                try:
                    btn.clicked.connect(
                        getattr(
                            self, bname.replace('uiRemove', 'remove').replace('BTN', '')
                        )
                    )
                except:
                    print 'error creating connection for', bname

        # create connections
        self.uiSaveBTN.clicked.connect(self.save)
        self.uiBuildBTN.clicked.connect(self.build)
        self.uiReleaseBTN.clicked.connect(self.release)
        self.uiCancelBTN.clicked.connect(self.reject)

    def addAuthor(self):
        from PyQt4.QtGui import QInputDialog

        text, accepted = QInputDialog.getText(self, 'Add Author', '')
        if text:
            self.uiAuthorsLIST.addItem(text)

    def addCommand(self):
        from PyQt4.QtGui import QInputDialog

        text, accepted = QInputDialog.getText(self, 'Add Command', '')
        if text:
            self.uiCommandsLIST.addItem(text)

    def addRequire(self):
        from PyQt4.QtGui import QInputDialog

        text, accepted = QInputDialog.getText(self, 'Add Requirement', '')
        if text:
            self.uiRequiresLIST.addItem(text)

    def build(self):
        from PyQt4.QtGui import QMessageBox as msg

        query = (
            'This will create a local build of %s v%s\n\nfrom:\n\n%s.\n\nContinue?'
            % (
                self.uiPackageTXT.text(),
                self.uiVersionTXT.text(),
                self.document().filename(),
            )
        )

        if msg.question(self, 'Releasing Project', query, msg.Yes | msg.No) == msg.No:
            return False

        # save the YAML file
        self.save()

        # change the directory & run the build command
        import os.path
        from blurdev import osystem

        osystem.shell(
            'drd-build -- -- install',
            basepath=os.path.dirname(self.document().filename()),
        )

    # define instance methods
    def document(self):
        """
            \remarks	returns the YamlDocument for this dialog
            \return		<YamlDocument>
        """
        return self._document

    def refresh(self):
        doc = self.document()

        # set ui information
        self.uiPackageTXT.setText(doc.value('name', ''))
        self.uiVersionTXT.setText(doc.value('version', ''))
        self.uiDescriptionTXT.setText(doc.value('description', ''))

        # add authors to tree list
        self.uiAuthorsLIST.addItems(doc.value('authors', []))

        # add config information
        self.uiConfigVersionTXT.setText(doc.value('config_version', '0'))
        self.uiUidTXT.setText(doc.value('uuid', ''))

        # add require information
        self.uiRequiresLIST.addItems(doc.value('requires', []))

        # add commands information
        self.uiCommandsLIST.addItems(doc.value('commands', []))

    def release(self):
        # pull out a message for the release
        from PyQt4.QtGui import QInputDialog as iput, QMessageBox as msg

        query = (
            'This will create a public build of %s v%s\n\nfrom:\n\n%s.\n\nContinue?'
            % (
                self.uiPackageTXT.text(),
                self.uiVersionTXT.text(),
                self.document().filename(),
            )
        )

        if msg.question(self, 'Releasing Project', query, msg.Yes | msg.No) == msg.No:
            return False

        message, accept = iput.getText(self, 'Release Message', 'Release Message')
        if not message:
            msg.critical(
                self,
                'No Message for Release',
                'You need to provide a message for the release',
            )
            return False

        # save the YAML file
        self.save()

        # change the directory & run the release command
        import os.path
        from blurdev import osystem

        basepath = os.path.dirname(self.document().filename())

        # run the release code
        osystem.shell('drd-release -m "%s"' % message, basepath=basepath)

        name = self.document().value('name')
        ver = self.document().value('version')

        # prompt the user for the next steps
        msg.critical(
            self,
            'Next Steps',
            '%s v%s has been released.\n\nNext steps:\n\n1. Update the %s Puppet file to %s\n2. Commit to SVN\n'
            % (name, ver, name, ver),
        )

        # update puppet
        if (
            msg.question(
                self,
                'Update Puppet',
                'Would you like to update Puppet right now?\n\nWarning: Only click yes if you completed the previous steps.',
                msg.Yes | msg.No,
            )
            == msg.Yes
        ):
            osystem.shell('/usr/local/bin/updatepuppet')

    def removeAuthor(self):
        from PyQt4.QtGui import QMessageBox as msg

        if (
            msg.question(
                self,
                'Remove Author',
                'Are you sure you want to remove these authors?',
                msg.Yes | msg.No,
            )
            == msg.Yes
        ):
            self.uiAuthorsLIST.takeItem(self.uiAuthorsLIST.currentRow())

    def removeCommand(self):
        from PyQt4.QtGui import QMessageBox as msg

        if (
            msg.question(
                self,
                'Remove Command',
                'Are you sure you want to remove these commands?',
                msg.Yes | msg.No,
            )
            == msg.Yes
        ):
            self.uiCommandsLIST.takeItem(self.uiCommandsLIST.currentRow())

    def removeRequire(self):
        from PyQt4.QtGui import QMessageBox as msg

        if (
            msg.question(
                self,
                'Remove Requirement',
                'Are you sure you want to remove these requirements?',
                msg.Yes | msg.No,
            )
            == msg.Yes
        ):
            self.uiRequiresLIST.takeItem(self.uiRequiresLIST.currentRow())

    def save(self):
        doc = self.document()

        doc.setValue('name', str(self.uiPackageTXT.text()))
        doc.setValue('version', str(self.uiVersionTXT.text()))
        doc.setValue('description', str(self.uiDescriptionTXT.toPlainText()))
        doc.setValue('config_version', str(self.uiConfigVersionTXT.text()))
        doc.setValue('uuid', str(self.uiUidTXT.text()))
        doc.setValue(
            'authors',
            [
                str(self.uiAuthorsLIST.item(index).text())
                for index in range(self.uiAuthorsLIST.count())
            ],
        )
        doc.setValue(
            'requires',
            [
                str(self.uiRequiresLIST.item(index).text())
                for index in range(self.uiRequiresLIST.count())
            ],
        )
        doc.setValue(
            'commands',
            [
                str(self.uiCommandsLIST.item(index).text())
                for index in range(self.uiCommandsLIST.count())
            ],
        )

        doc.save()

    def setFilename(self, filename):
        """
            \remarks	sets the filename for my parameter to the inputed filename
            \param		filename	<variant>
        """
        from blurdev.ide.addons.yaml.yamldocument import YamlDocument

        document = YamlDocument()
        if document.load(filename):
            self._document = document
            self.refresh()

    # define static methods
    @staticmethod
    def edit(filename):
        import blurdev

        dlg = YamlDialog(blurdev.core.activeWindow())
        dlg.setFilename(filename)
        dlg.show()
        return True
