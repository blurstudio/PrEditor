import time
import blurdev.external


class PdbBase(object):
    def external(self):
        """ Opens the logger in a sub process if it is not open and returns the connection 
        
        Returns:
            blurdev.external.External: Class to send messages to
        """
        return blurdev.external.External(['blurdev', 'showLogger'])


class PdbInput(PdbBase):
    def readline(self):
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
                print '**************** Lost Connection to pdb logger, exiting pdb via continue ****************'
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
            msg = '**************** Exit pdb command detected, exiting Pdb Mode ****************'
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
