##
#   :namespace  python.blurdev.protocols
#
#   :remarks    Handlers are classes that process the command and arguments into functioning code.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       01/12/15
#

from future.utils import iteritems
from past.builtins import basestring
import sys as _sys
import os as _os
import subprocess as _subprocess
import cPickle as _cPickle
import blurdev as _blurdev


class InvalidHandler(Exception):
    """ Returned to the pipe if a invalid request was provided """

    pass


class BaseProtocolHandler(object):
    name = 'base'
    eval_params = True

    def __init__(self, command, params):
        super(BaseProtocolHandler, self).__init__()
        self.command = command
        self.params = params
        if self.eval_params:
            self.params = self.evalParams(self.params)

    @classmethod
    def evalParams(cls, params):
        """ Takes a dict, evals and re-sets all the values and returns the dict. """
        for key, value in params.items():
            try:
                if isinstance(value, list):
                    value = [eval(v) for v in value]
                else:
                    value = eval(value)
            except Exception:
                pass
            else:
                params[key] = value
        return params

    @classmethod
    def findHandler(cls, name, command, params):
        """ Returns the handler class based off the handler name.
        
        Loops through BaseProtocolHandler.__subclasses__() and checks if name matches and
        returns the a instance of the first match.
        
        Args:
            name(str): The name of the handler
            command: The command argument passed to the handler
            params(dict): The params argument passed to the handler
        """
        # TODO: make this use a plugin system for loading handlers.
        for handler in cls.__subclasses__():
            if handler.name == name:
                return handler(command, params)
        else:
            return cls(command, params)

    def run(self):
        print(self.name, self.command, self.params)


class TreegruntHandler(BaseProtocolHandler):
    name = 'treegrunt'

    def run(self):
        # This is going to take a while, show the splashscreen to
        # entertain the user while they wait for the index to load
        from blurdev.gui.splashscreen import randomSplashScreen

        _blurdev.protocolSplash = randomSplashScreen(self.command)

        tool = _blurdev.findTool(self.command)
        if not tool.isNull():
            _os.environ['BDEV_URL_ARGS'] = _cPickle.dumps(self.params)
            tool.exec_()


class BlurdevHandler(BaseProtocolHandler):
    """ Used to run specific blurdev commands.
    
    Can be used to show the logger and treegrunt. If you use the TreegruntHandler to show the logger 
    in the external treegrunt, it will launch a new python process for the logger, which is not what 
    we want to happen.
    """

    name = 'blurdev'

    def run(self):
        if self.command == 'showLogger':
            _blurdev.core.showLogger()
        elif self.command == 'showTreegrunt':
            _blurdev.core.showTreegrunt()


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
            _sys.stdout.write(msg)
        elif self.command == 'stderr':
            _sys.stderr.write(msg)
        elif self.command == 'print':
            print(msg)
        if pdbMode == False:
            # disable pdbMode after the message was written because the message often contains the
            # (pdb) prompt.
            from blurdev.gui.windows.loggerwindow import LoggerWindow

            LoggerWindow.instanceSetPdbMode(pdbMode)


class ShotgunActionMenuItemHandler(BaseProtocolHandler):
    name = 'shotgun'
    eval_params = False

    def __init__(self, command, params):
        super(ShotgunActionMenuItemHandler, self).__init__(command, params)

        # May contain subcommands, strip those out so that the correct tool
        # can be found based off the main command.  Subcommands will be passed
        # to the tool via params value.
        cmd_split = self.command.split('/')
        if len(cmd_split) > 1:
            self.command = cmd_split[0]

        # Support Light payload urls
        if 'event_log_entry_id' in params:
            for cmd in cmd_split:
                # Light Payload urls don't include useful info like what server
                # the request was made from, so light Payload shotgun urls require
                # a hostname argument passed.
                # Example Action Menu url column:
                # 	blurdev://shotgun/shotgunmultiedit/sg_url=mysite.shotgunstudio.com/
                if cmd.startswith('sg_url='):
                    logId = int(params['event_log_entry_id'])
                    hostname = cmd.replace('sg_url=', '')

                    # This is going to take a while, show the splashscreen to
                    # entertain the user while they wait for a shotgun select
                    from blurdev.gui.splashscreen import randomSplashScreen

                    _blurdev.protocolSplash = randomSplashScreen(self.command)

                    import blursg

                    with blursg.loadConfigContext(hostname=hostname):
                        ret = blursg.sg().find_one(
                            'EventLogEntry', [['id', 'is', logId]], ['meta']
                        )
                        params = ret['meta']['ami_payload']

                    # Make it easy to see info about the payload in the log file. The
                    print(params)

                    # Nothing else to do
                    break

        new_params = {}
        new_params['command'] = command
        new_params['columns'] = params.get('cols', [])
        new_params['column_display_names'] = params.get('column_display_names', [])
        new_params['entity_type'] = params.get('entity_type', '')
        new_params['ids'] = [int(i) for i in params.get('ids', '').split(',')]
        new_params['ids_filter'] = [['id', 'in', new_params['ids']]]
        new_params['project'] = None
        new_params['selected_ids'] = [
            int(i) for i in params.get('selected_ids', '').split(',')
        ]
        new_params['selected_ids_filter'] = [['id', 'in', new_params['selected_ids']]]
        if 'sort_column' in params and 'sort_direction' in params:
            new_params['sort'] = [
                {'column': params['sort_column'], 'direction': params['sort_direction']}
            ]
        else:
            new_params['sort'] = None
        new_params['title'] = params.get('title', '')
        new_params['user'] = {'id': params['user_id'], 'login': params['user_login']}
        new_params['params'] = params
        self.params = new_params

    def run(self):
        # short circuit tool path finding (speedier)
        # TODO: Check for and parse the xml file instead of expecting the exec file to be main.pyw.
        tool_path = _os.path.normpath(
            _os.path.join(
                _blurdev.activeEnvironment().path(),
                'code/python/tools',
                self.command,
                'main.pyw',
            )
        )
        if _os.path.isfile(tool_path):
            _os.environ['BDEV_URL_ARGS'] = _cPickle.dumps({'params': self.params})
            from blurdev.tools import Tool

            tool = Tool()
            tool.setSourcefile(tool_path)
            tool.exec_()
        else:
            # Fallback to find tools that don't use the simple pathing.
            tool = _blurdev.findTool(self.command)
            if not tool.isNull():
                _os.environ['BDEV_URL_ARGS'] = _cPickle.dumps({'params': self.params})
                tool.exec_()
