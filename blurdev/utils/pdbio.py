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
        while not hasData:
            # No data in the pipe, check again after a small delay
            time.sleep(0.1)
            hasData, data = external.checkPipe()
        else:
            if data[0] == 'pdb':
                out = data[2]['msg']
            else:
                # Not our data, process data normally
                external.handleData(data)
        # restore the timer checking the pipe if it was active
        if active:
            external.startCheckingPipe(interval)
        return out


class PdbOutput(PdbBase):
    def flush(self):
        pass

    def write(self, msg):
        self.external().writeToPipe(msg)
