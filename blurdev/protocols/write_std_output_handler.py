import sys

from future.utils import iteritems

from blurdev.protocols import BaseProtocolHandler, InvalidHandler


class WriteStdOutputHandler(BaseProtocolHandler):
    """ Writes the msg param to the requested output

    Valid commands are 'stdout', 'print', 'stderr'. stdout and stderr write to their sys counterparts.
    print(calls print. You must pass the parameter 'msg' as a string, this will be written to the 
)
    requested output. You can optionally pass a boolean to 'pdb', if the instance of the
    LoggerWindow exists it will enable or disable pdb mode on it.

    Sometimes when sending a string like '161  \t\t\n' msg will end up as the int 161. In cases like
    this you can pass the optional keyword 'wrapper' containing a string like '!!!'. If you use wrapper
    you must add the wrapper string to the start and end of your string. If these are missing it will
    send a InvalidHandler exception back up the pipe. These wrappers will be removed before the message
    is written.
    """

    name = 'stdoutput'

    @classmethod
    def unwrapMessage(cls, msg, wrapper):
        # Passing values like '161  \t\t\n' along the pipe ends up with just a int. To get around
        # this I am adding a wrapper string to the start and end of the msg. so we need to remove
        # the wrapper characters.
        length = len(wrapper)
        if len(msg) < length or (msg[:length] != wrapper or msg[-length:] != wrapper):
            errorMsg = (
                'The wrapper "{wrapper}" could not be found in the message\n{msg}'
            )
            import blurdev.external

            blurdev.external.External(
                InvalidHandler(errorMsg.format(wrapper=wrapper, msg=msg))
            )
            return False, msg
        return True, msg[length:-length]

    def run(self):
        msg = self.params['msg']
        pdbMode = self.params.get('pdb')
        pdbResult = self.params.get('pdbResult')
        wrapper = self.params.get('wrapper')
        if wrapper:
            success, msg = self.unwrapMessage(msg, wrapper)
            if not success:
                return
        if pdbMode == True and msg.strip():
            # Don't trigger pdb mode if a empty(including new lines) string was sent
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            LoggerWindow.instanceSetPdbMode(pdbMode, msg)
        if pdbResult:
            # Some Pdb data was requested, have the logger handle it.
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            data = {}
            for key, value in iteritems(self.params):
                if isinstance(value, basestring):
                    success, value = self.unwrapMessage(value, wrapper)
                data[key] = value
            LoggerWindow.instancePdbResult(data)
            return
        if self.command == 'stdout':
            sys.stdout.write(msg)
        elif self.command == 'stderr':
            sys.stderr.write(msg)
        elif self.command == 'print':
            print(msg)
        if not pdbMode:
            # disable pdbMode after the message was written because the message often contains the
            # (pdb) prompt.
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            LoggerWindow.instanceSetPdbMode(pdbMode)
