import blurdev, subprocess, os, sys
from blurdev.gui import Dialog
from PyQt4.QtCore import Qt, QTimer
from PyQt4.QtGui import QPixmap


class ErrorDialog(Dialog):
    def __init__(self, parent):
        super(ErrorDialog, self).__init__(parent)

        blurdev.gui.loadUi(__file__, self)

        self.parent_ = parent
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
        from console import ConsoleEdit

        toolPath = os.path.join(
            blurdev.activeEnvironment().path(),
            'code',
            'python',
            'tools',
            'RequestPimp',
            'main.pyw',
        )

        if 'python' in sys.executable:
            python_exe = sys.executable
        else:
            if sys.platform == 'win32':
                python_exe = r'C:\python27\pythonw.exe'
            else:
                python_exe = r'/usr/bin/pythonw'

        longsubject, body = ConsoleEdit.buildErrorMessage(
            self.traceback_msg, format='textile'
        )
        subject = self.traceback_msg.split('\n')[-2]
        subprocess.Popen(
            [
                python_exe,
                toolPath,
                '--project',
                'pipeline',
                '--subject',
                subject,
                '--additional-info',
                body,
                '--dry-run',
            ]
        )
        QTimer.singleShot(5000, self.close)
        self.setCursor(Qt.WaitCursor)
