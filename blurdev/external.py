from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import time
import multiprocessing
from multiprocessing import Process, Pipe
import blurdev
from Qt.QtCore import QTimer
from blurdev.protocols import BaseProtocolHandler, InvalidHandlerError
import six

try:
    # Optional: In case blur.Stone is not installed,
    # though this will mean it can't automatically close python.
    import blur.Stone as Stone
except ImportError:
    Stone = None


class External(object):
    """Singleton class used for multiProcess communication.

    This class provides a easy way to spawn a secondary instance of python and run
    Qt/blurdev. It also provides for two way communication between the two processes.
    Currently, the parent process does not check its pipe for data automatically, you
    will need to periodicly poll that data using checkPipe if you would like to receive
    that info.

    Note: This uses blur.Stone to monitor the parent process though it is optional, if
        blur.Stone is not installed, it may not properly close the subprocesses.

    Args:
        send: If provided, call multiProcess, and send the data. Defaults to None. See
            parsePipe for valid values.

    Attributes:

        checkIfOrphaned (bool): If true, exit blurdev if the parent process terminates

        childProcess (multiprocessing.Process): Pointer to the child process

        exitMonitorPid (int): Parent process id used to check if the parent process has
        terminated.

        exitMonitorProcessName (str): Parent process name used to check if the parent
            process has terminated. Because of how multiprocessing works this becomes
            invalid before the pid. In most cases the pid will not become invalid until
            the child python closes.

        isChildProcess (bool): If true, this is the child process, otherwise it is the
            parent process.

        timerCommand (QTimer): QTimer used to to check if there is data in the pipe, and
            check if the parent process has closed.

        parentCore (str): The name of the core that launched the child process. It is
            used to handleData any core specific configuration required like not
            parenting to the parent app.

    Example:

        In the parent process, this will spawn a child process if neccissary, and send
        ['treegrunt', 'Python_Logger'] to the child process. In this case it will launch
        the Python_Logger tool. In the child process, it would send the message back up
        the pipe to the parent process.

        >>> import blurdev.external
        >>> blurdev.external.External(['treegrunt', 'Python_Logger'])
    """

    _instance = None

    def __new__(cls, send=None):
        if not cls._instance:
            cls._instance = super(External, cls).__new__(cls, send=send)
            cls._parentPipe = None
            cls._childPipe = None
            cls.checkIfOrphaned = False
            cls.childProcess = None
            cls.exitMonitorPid = None
            cls.exitMonitorProcessName = ''
            cls.isChildProcess = False
            cls.timerCommand = None
            cls.parentCore = ""
        return cls._instance

    def __init__(self, send=None):
        super(External, self).__init__()
        if send:
            self.multiProcess()
            self.send(send)

    def checkPipe(self):
        """Poll the pipe to see if it contains data and return if it does and the data.

        If the pipe is broken because the parent process was closed, it will call
        shutdownIfParentClosed if checkIfOrphaned is enabled.

        Returns:
            bool: If the pipe had data
            var: The data stored in the pipe
        """
        pipe = self.pipe()
        try:
            if pipe and pipe.poll():
                data = pipe.recv()
                return True, data
        except IOError as e:
            if e.errno == 109:
                # The pipe has been ended, shutdown blurdev and exit python even if the
                # parent process is still running
                if self.checkIfOrphaned:
                    self.shutdownIfParentClosed(force=True)
        return False, None

    def handleData(self, data):
        """Parses the data returned from the pipe and calls the proper handler.

        Processes data retreived from the pipe, and uses
        blurdev.protocols.BaseProtocolHandler to process the contents of data. Valid
        data should be in the form of ['handlerName', 'handlerCommand'] or
        ['handlerName', 'handlerCommand', {'keyword', 'args'}]. It will also accept a
        Exception as the only data. If a Exception is received it will be raised. If a
        invalid request is received, it will send a InvalidHandlerError exception back
        up the pipe.

        Args:
            data (list): ['handlerName', 'handlerCommand', {'keyword', 'args'}]

        Returns:
            bool: If a handler was found
        """
        name = None
        command = None
        params = {}
        if isinstance(data, Exception):
            raise data
        if isinstance(data, (list, tuple)) and len(data) > 1:
            # Lists/tuple's are only valid if they contain an id string and a dictionary
            name = data[0]
            command = data[1]
            # params are optional
            if len(data) > 2:
                params = data[2]
            handler = data
        if (
            not isinstance(name, six.string_types)
            or not isinstance(command, six.string_types)
            or not isinstance(params, dict)
        ):
            print("Invalid data", [name, command, params])
            msg = (
                "Please provide valid command handler arguments. Example: "
                "['handlerName', 'handlerCommand', {'keyword', 'args'}]"
            )
            self.send(InvalidHandlerError(msg))
            return
        handler = BaseProtocolHandler.findHandler(name, command, params)
        if handler:
            handler.run()
            return True
        return False

    def childIsAlive(self):
        if not self.isChildProcess:
            return self.childProcess.is_alive()
        return False

    @classmethod
    def launch(
        cls,
        hwnd,
        childPipe=None,
        exitMonitorPid=None,
        exitMonitorProcessName='',
        parentCore='',
        compid=None,
    ):
        """Used to initialize a new instance of python and start the Qt Event loop.

        This function configures blurdev and starts Qt. It calls QApplication.exec_()
        and will not exit until blurdev is shutdown.

        Args:
            hwnd(int): The win32 id used to parent Qt to the parent process
            childPipe(multiProcess.Pipe):
                The Pipe used for inter-process communication.
                Defaults to None.
            exitMonitorPid(int):
                Shutdown blurdev when this pid becomes invalid.
                Defaults to None.
            exitMonitorProcessName(str):
                Used with exitMonitorPid.
                Closing applications with a multiprocessing instance running often
                does not invalidate the pid, but changes the process name, checking
                both, allows us to detect that the process has closed
                even though the pid is still valid. Defaults to None.
            compid(string):
                A unique id used by Fusion to connect to the correct fusion if more than
                one fusion is open. Defaults to None.
        """
        instance = cls()
        instance.exitMonitorProcessName = exitMonitorProcessName
        instance.isChildProcess = True
        instance.parentCore = parentCore
        # Diffrent parent cores have diffrent requirements.
        # Studiomax and other software cores are not importable externally,
        # so we need to identify them by their object name.
        parentCore = parentCore.lower()
        if parentCore != "studiomax":
            blurdev.core.setHwnd(hwnd)
            blurdev.core._mfcApp = True
        if childPipe:
            # Monitor the pipe for communications from the parent application
            instance._childPipe = childPipe
            instance.startCheckingPipe(100)
        if exitMonitorPid and Stone:
            # Make parsePipe check if the parent process was closed, if so exit qt.
            instance.exitMonitorPid = exitMonitorPid
            instance.checkIfOrphaned = True
        elif exitMonitorPid and Stone is None:
            print(
                "blur.Stone is not installed, "
                "so this will not close automatically, or properly save prefs"
            )
        blurdev.core.setObjectName("multiprocessing")
        # Notes: studiomax: max crashes if app.quitOnLastWindowClosed is False.
        #       fusion:if True, closing any window/dialog will cause qt to close and
        #       python to exit external: pdb auto continue on close is not triggered if
        #       app.quitOnLastWindowClosed is false
        if parentCore == "fusion" or (
            parentCore != "studiomax" and not instance.checkIfOrphaned
        ):
            # If this is not set, Qt will close when ever a QDialog or QMainWindow is
            # closed
            app = blurdev.application
            app.setQuitOnLastWindowClosed(False)
        # This is neccissary as long as our stylesheets depend on Plastique as a base.
        blurdev.application.setStyle(blurdev.core.defaultStyle())
        # Initialize the logger
        blurdev.core.logger()
        # Start Qt's event loop
        blurdev.startApplication()

    def multiProcess(self):
        """Spawns or returns instance of python and the Pipe to communicate with.

        It is safe to call this method multiple times in both the parent and child
        processes. It will only spawn a new instance of python in the parent process if
        the child process has been closed, or never launched. When called in the child
        process it does nothing
        """
        # Only create the subprocess if it hasn't already been created
        if self.isChildProcess or (self.childProcess and self.childProcess.is_alive()):
            return self.childProcess, self._parentPipe
        # NOTE: I am using a blur.Stone function to monitor if the parent app is closed.
        # If blur.Stone in not installed, you need a way to close it. For now I am
        # showing a python console. In the future I may extract the win32 code so it can
        # be checked, but it will probably be slower.
        exe = "python.exe"
        daemon = True
        if Stone:
            exe = "pythonw.exe"
            daemon = False
        exe = os.path.join(sys.exec_prefix, exe)
        # Nuke's sys.exec_prefix is the root directory on windows. Should I just use
        # pythonPath?
        if not os.path.exists(exe):
            exe = blurdev.osystem.pythonPath(pyw=bool(Stone))
        multiprocessing.set_executable(exe)
        if not hasattr(sys, "argv"):
            # multiprocessing requires sys.argv so manually create it if it doesn't
            # already exist
            sys.argv = ['']
        # Get all neccissary info to properly parent, communicate and detect closing
        hwnd = blurdev.core.hwnd()  # used to parent Qt to parent app
        compid = (
            blurdev.core.uuid()
        )  # Id used by 3rd party api's to connect to parent app
        pid = os.getpid()  # Detect if parent app was closed

        self._parentPipe, self._childPipe = Pipe()
        kwargs = {"compid": compid}
        kwargs["childPipe"] = self._childPipe
        kwargs["exitMonitorPid"] = pid
        kwargs["parentCore"] = blurdev.core.objectName()
        self.childProcess = Process(target=External.launch, args=(hwnd,), kwargs=kwargs)
        self.childProcess.daemon = daemon
        self.childProcess.start()
        return self.childProcess, self._parentPipe

    def parsePipe(self):
        """Callback used to monitor for incoming commands and execute them.

        If checkIfOrphaned is True, and exitMonitorPid is populated,
        it will check if the process is still running, if not,
        it will call blurdev.core.shutdown() and allow python to close without
        processing any queued pipe items.
        """
        if self.checkIfOrphaned and self.exitMonitorPid:
            if self.shutdownIfParentClosed():
                return
        hasData, data = self.checkPipe()
        # Clear out all pending data in the pipe
        while hasData:
            self.handleData(data)
            hasData, data = self.checkPipe()

    def pipe(self):
        """Returns the pipe used to communicate with the other end of the application.

        Returns:
            multiprocessing.Pipe: used to communicate with the other process
        """
        if self.isChildProcess:
            return self._childPipe
        return self._parentPipe

    def send(self, data):
        """Sends a command to be handled in the other process

        Commands must be a list. The first item is the name of the handler.
        The second item is the
        command to send to the handler.
        You can optionally pass a dictionary of kwargs as the third argument.

        See Also: blurdev.protocols

        Args:
            data(list): Command to send.

        Returns:
            bool: If data was sent
        """
        pipe = self.pipe()
        if pipe:
            pipe.send(data)
            return True
        return False

    def shutdownIfParentClosed(self, force=False):
        """Shutdown blurdev if parent process is closed.

        Uses blur.Stone to check if the parent process is still running, if not,
        it calls blurdev.core.shutdown() to close qt and allow python to exit.

        Args:
            force(bool): Ignore blur.Stone check and force blurdev to shutdown.
        """
        if force or not Stone.isRunning(
            self.exitMonitorPid, self.exitMonitorProcessName
        ):
            args = {"app": self.parentCore.capitalize()}
            msg = "{app} is no longer running, shutting down blurdev and saving prefs"
            print(msg.format(**args))
            if "python.exe" in sys.executable.lower():
                time.sleep(1)
            blurdev.core.shutdown()
            return True
        return False

    def startCheckingPipe(self, interval):
        """Starts a QTimer that calls parsePipe at the provided interval.

        This will process all pre-existing messages in the pipe

        Args:
            interval (int): The number of milliseconds between calling parsePipe
        """
        if not self.timerCommand:
            self.timerCommand = QTimer(blurdev.core)
            self.timerCommand.timeout.connect(self.parsePipe)
        self.timerCommand.start(interval)

    def stopCheckingPipe(self):
        """Stops the timerCommand QTimer."""
        if self.timerCommand:
            self.timerCommand.stop()

    def writeToPipe(self, msg, error=False):
        command = "stderr" if error else "stdout"
        # use wrapper to ensure that the pickle process
        # doesn't end up creating a int or something.
        self.send(
            [
                "stdoutput",
                command,
                {"msg": "!!!{}!!!".format(msg), "pdb": True, "wrapper": "!!!"},
            ]
        )
