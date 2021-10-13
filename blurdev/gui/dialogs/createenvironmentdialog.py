from __future__ import absolute_import
import os
import blurdev
from blurdev.tools.toolsenvironment import ToolsEnvironment
from pillar.live_subprocess import LiveSubprocess
from pillar.virtualenv_helper import VirtualenvHelper
from Qt.QtWidgets import QApplication, QDialogButtonBox, QMessageBox


class CreateEnvironmentDialog(blurdev.gui.Dialog):
    def __init__(self, config, filename, parent=None, name='', path='', email=''):
        super(CreateEnvironmentDialog, self).__init__(parent)
        blurdev.gui.loadUi(__file__, self)

        # Store the valid state of each valid check, only enable the OK button
        # if all of them are True
        self._config_valid = True
        self._name_valid = True

        # Generate a cache of the environment names for validation. This must be done
        # before we edit any text in `self.uiNameTXT`.
        self._name_cache = set()
        for cfg in config.values():
            for env in cfg.get('environments', []):
                env_name = env.get('name')
                if env_name:
                    self._name_cache.add(env_name)

        self.uiEnvironmentLBL.setText(filename)
        # Don't call the callback at this point if name is set. We will manually call
        # it at the end of __init__.
        self.uiNameTXT.blockSignals(True)
        self.uiNameTXT.setText(name)
        self.uiNameTXT.blockSignals(False)
        self.uiPathWGT.setFilePath(path)
        self.uiEmailTXT.setText(email)

        self.config = config
        self.filename = filename

        # Update the text shown by uiValidSTACK if the provided filename is not valid
        self.uiInvalidConfigLBL.setText(
            '"{}"\nThe filename was not found in the provided configuration.'.format(
                self.filename
            )
        )

        self.validate_config()
        self.validate_name()

    def accept(self):
        # Validate the environment name
        name = self.uiNameTXT.text()
        if not name:
            QMessageBox.critical(
                self, 'Missing Name', 'You must specify a display name.'
            )
            return

        # Validate the file path
        path = self.uiPathWGT.filePath()
        if not path:
            QMessageBox.critical(
                self, 'Invalid Path', 'You must specify a virtualenv path.'
            )
            return
        if not self.uiCreateVirtualenvCHK.isChecked() and not os.path.exists(path):
            QMessageBox.critical(
                self,
                'Missing virtualenv',
                "Create Virtualenv is unchecked and the specified path doesn't exist.",
            )
            return

        directory, folder = os.path.split(path)
        msg = (
            'Are you sure you want to create this virtual environment? It will create '
            'a virtualenv named "{folder}" in <a href="{directory}">{directory}</a>?'
        )
        ret = QMessageBox.question(
            self,
            'Create Treegrunt Environment?',
            msg.format(folder=folder, directory=directory),
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.No:
            return

        # All of the validation is finished actually create the environment
        # 1. Create the virtualenv
        if self.uiCreateVirtualenvCHK.isChecked():
            returncode, output = VirtualenvHelper.create_virtualenv(
                path, callback=self.writeText
            )
            if returncode:
                msg = (
                    "The virtualenv process returned error code: {code}"
                    "Continue to create the treegrunt environment?"
                    "{output}"
                )
                ret = QMessageBox.critical(
                    self,
                    'Problem creating virtualenv',
                    msg.format(code=returncode, output=output),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.No:
                    return

        # 2. Find the site-packages folder for the newly created virtualenv
        path = VirtualenvHelper.site_packages(path)

        # 3. Add the new environment to the config
        env = ToolsEnvironment.create_env(name, path, email=self.uiEmailTXT.text())
        self.config[self.filename].setdefault('environments', []).append(env)
        # Save the config changes to disk
        ToolsEnvironment.save_config(self.config)

        if self.uiAddPthCHK.isChecked():
            # 4. Add the .pth file the user requested
            pth_file = os.path.join(path, 'treegrunt.pth')
            source_env = self.uiPthEnvironmentDDL.currentEnvironment()
            with open(pth_file, 'w') as fle:
                fle.write('{}\n'.format(source_env.path()))

            # 5. Rebuild the treegrunt index
            proc = LiveSubprocess(
                ["blurdev", "env", "rebuild", '--name', name],
                callback=self.writeText,
                env=blurdev.osystem.subprocessEnvironment(),
            )
            proc.wait()
            if proc.returncode:
                QMessageBox.critical(
                    self,
                    "Error rebuilding index",
                    (
                        "The new treegrunt environment has been created, but there was "
                        "a problem rebuilding the index. You can try to use the "
                        "environment at this point.\n\n{}"
                    ).format(proc.output),
                )
                # Don't close the dialog so the user can look at all of the output
                return

        super(CreateEnvironmentDialog, self).accept()

    def update_validated_buttons(self):
        self.uiButtonBOX.button(QDialogButtonBox.Ok).setEnabled(self.valid)

    @property
    def valid(self):
        return self._config_valid and self._name_valid

    def validate_config(self):
        self._config_valid = self.filename in self.config
        # Hide the form if the filename is not valid
        self.uiValidSTACK.setCurrentIndex(0 if self._config_valid else 1)
        self.update_validated_buttons()

    def validate_name(self):
        """Check that the name is not blank or already in use and update the ui."""
        name = self.uiNameTXT.text()
        self._name_valid = bool(name) and name not in self._name_cache
        if self._name_valid:
            self.uiNameTXT.setStyleSheet('')
        else:
            self.uiNameTXT.setStyleSheet('background: red')
        self.update_validated_buttons()

    def writeText(self, txt):
        """Writes text to the output text box so it can be read by the user."""
        # move the cursor to the end of the document
        c = self.uiOutputTXT.textCursor()
        c.movePosition(c.End)
        self.uiOutputTXT.setTextCursor(c)

        self.uiOutputTXT.insertPlainText('{}\n'.format(txt))
        # Scroll to the bottom of the output text
        sb = self.uiOutputTXT.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.instance().processEvents()
