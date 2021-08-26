from __future__ import print_function
from __future__ import absolute_import
import time
import blurdev.external
from pdb import Pdb


class BlurPdb(Pdb):
    def currentLine(self):
        """ Returns the current frame's filename and line number

        Returns:
            str: The filename pdb is currently at.
            int: The line number pdb is currently at.
        """
        filename = self.curframe.f_code.co_filename
        lineNo = self.curframe.f_lineno - 1
        # Send the data to the remote pdb session
        data = {
            'pdbResult': True,
            'msg': '!!!pdb_currentLine!!!',
            'filename': '!!!{}!!!'.format(filename),
            'pdb': True,
            'wrapper': '!!!',
            'lineNo': lineNo,
        }
        blurdev.external.External(['stdoutput', 'stdout', data])
        return filename, lineNo

    def do_up(self, arg):
        Pdb.do_up(self, arg)
        self.currentLine()

    do_u = do_up

    def do_down(self, arg):
        Pdb.do_down(self, arg)
        self.currentLine()

    do_d = do_down

    def do_step(self, arg):
        ret = Pdb.do_step(self, arg)
        self.currentLine()
        return ret

    do_s = do_step

    def do_next(self, arg):
        ret = Pdb.do_next(self, arg)
        self.currentLine()
        return ret

    do_n = do_next


class PdbBase(object):
    def external(self):
        """ Opens the logger in a sub process if it is not open and returns the
        connection

        Returns:
            blurdev.external.External: Class to send messages to
        """
        return blurdev.external.External(['blurdev', 'showLogger'])


class PdbInput(PdbBase):
    # autoUp is used to move the current frame above blurdev.debug.set_trace. This makes
    # the current frame into your code, not inside the blurdev.debug.set_trace function.
    _autoUp = False

    @classmethod
    def autoUp(cls):
        return cls._autoUp

    @classmethod
    def setAutoUp(cls, state):
        cls._autoUp = state

    def readline(self):
        # If autoUp is enabled we need to tell pdb to move up the current frame up to
        # where the user actually called the pdb command.
        if self.autoUp():
            self.setAutoUp(False)
            return "up"
        out = ''
        active = False
        # Stop the timer checking the pipe so our pdb commands don't disapear
        external = self.external()
        if external.timerCommand:
            active = external.timerCommand.isActive()
            if active:
                interval = external.timerCommand.interval()
                external.stopCheckingPipe()
        hasData, data = external.checkPipe()
        isAlive = external.childIsAlive()
        while not hasData and isAlive:
            # No data in the pipe, check again after a small delay
            time.sleep(0.1)
            isAlive = external.childIsAlive()
            hasData, data = external.checkPipe()
        else:
            if not isAlive:
                txt = ' Lost Connection to pdb logger, exiting pdb via continue '
                print(txt.center(100, '*'))
                out = 'continue'
            else:
                if data[0] == 'pdb':
                    out = data[2]['msg']
                else:
                    # Not our data, process data normally
                    external.handleData(data)
        # restore the timer checking the pipe if it was active
        if active:
            external.startCheckingPipe(interval)
        # Exiting pdb, tell the pdb logger to exit pdbMode
        # TODO: Should I subclass pdb.Pdb to handle this directly?
        if out == '' or out in ('continue', 'EOF', 'exit'):
            msg = ' Exit pdb command detected, exiting Pdb Mode '.center(100, '*')
            external.send((['stdoutput', 'stdout', {'msg': msg, 'pdb': False}]))
        return out


class PdbOutput(PdbBase):
    def flush(self):
        pass

    def write(self, msg):
        self.external().send(
            [
                'stdoutput',
                'stdout',
                {'msg': '!!!{}!!!'.format(msg), 'pdb': True, 'wrapper': '!!!'},
            ]
        )
