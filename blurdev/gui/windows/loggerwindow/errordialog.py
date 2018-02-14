import blurdev, subprocess, os, sys
from blurdev.gui import Dialog
from PyQt4.QtCore import Qt, QTimer
from PyQt4.QtGui import QPixmap


class ErrorDialog(Dialog):
    def __init__(self, parent):
        super(ErrorDialog, self).__init__(parent)

        blurdev.gui.loadUi(__file__, self)

        self.parent_ = parent
        self.requestPimpPID = None
        self.setWindowTitle('Error Occurred')
        self.errorLabel.setTextFormat(Qt.RichText)
        self.iconLabel.setPixmap(
            QPixmap(
                os.path.join(
                    os.path.dirname(blurdev.__file__),
                    'resource',
                    'img',
                    'warning-big.png',
                )
            ).scaledToHeight(64, Qt.SmoothTransformation)
        )

        self.loggerButton.clicked.connect(self.showLogger)
        self.requestButton.clicked.connect(self.submitRequest)
        self.ignoreButton.clicked.connect(self.close)

    def setText(self, traceback_msg):
        from console import ConsoleEdit

        msg = 'The following error has occurred:<br><br><font color=%(color)s>%(text)s</font>'
        self.errorLabel.setText(
            msg
            % {
                'text': traceback_msg.split('\n')[-2],
                'color': ConsoleEdit._errorMessageColor.name(),
            }
        )
        self.traceback_msg = traceback_msg

    def showLogger(self):
        inst = blurdev.gui.windows.loggerwindow.LoggerWindow.instance()
        inst.show()
        self.close()

    def submitRequest(self):
        from blurdev.utils.errorEmail import buildErrorMessage

        toolPath = blurdev.findTool('RequestPimp').sourcefile()

        if 'python' in sys.executable:
            python_exe = sys.executable
        else:
            if sys.platform == 'win32':
                python_exe = blurdev.osystem.pythonPath(pyw=True)
            else:
                python_exe = r'/usr/bin/pythonw'

        longsubject, body = buildErrorMessage(self.traceback_msg, fmt='textile')
        subject = self.traceback_msg.split('\n')[-2]
        cmd = [
            python_exe,
            toolPath,
            '--project',
            'pipeline',
            '--subject',
            subject,
            '--additional-info',
            body,
        ]
        process = subprocess.Popen(cmd, env=blurdev.osystem.subprocessEnvironment())
        self.requestPimpPID = process.pid
        QTimer.singleShot(1000, self.waitForRequestPimp)
        self.setCursor(Qt.WaitCursor)

    def waitForRequestPimp(self):
        # don't attempt this unless we're on the best OS evar
        if not sys.platform == 'win32':
            QTimer.singleShot(5000, self.close)
            return
        try:
            # checks if the pdplayer window has opened yet
            import win32gui, win32process
        except ImportError:
            QTimer.singleShot(5000, self.close)
            return
        from PyQt4.QtGui import QMessageBox

        def handleGet(handle, args):
            if win32gui.IsWindowVisible(handle) and win32gui.IsWindowEnabled(handle):
                junk, found_pid = win32process.GetWindowThreadProcessId(handle)
                if found_pid == self.requestPimpPID:
                    args.append(handle)

        handles = []
        win32gui.EnumWindows(handleGet, handles)

        if handles:
            self.close()
        else:
            pids = win32process.EnumProcesses()
            if self.requestPimpPID in pids:
                QTimer.singleShot(100, self.waitForRequestPimp)

            else:
                self.setCursor(Qt.ArrowCursor)
                errorstr = (
                    'RequestPimp (%s) seems to have crashed before launching.'
                    % str(self.requestPimpPID)
                )
                QMessageBox.warning(self, 'Error', errorstr, QMessageBox.Ok)
