##
#   :namespace  python.blurdev.protocols
#
#   :remarks    Handlers are classes that process the command and arguments into functioning code.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       01/12/15
#

import os as _os
import subprocess as _subprocess
import cPickle as _cPickle
import blurdev as _blurdev


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
        print self.name, self.command, self.params


class TreegruntHandler(BaseProtocolHandler):
    name = 'treegrunt'

    def run(self):
        tool = _blurdev.findTool(self.command)
        if not tool.isNull():
            _os.environ['BDEV_URL_ARGS'] = _cPickle.dumps(self.params)
            tool.exec_()


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
            process = _subprocess.Popen([r'C:\python27_64\pythonw.exe', tool_path])
            process.wait()

        else:
            # Fallback to find tools that don't use the simple pathing.
            tool = _blurdev.findTool(self.command)
            if not tool.isNull():
                _os.environ['BDEV_URL_ARGS'] = _cPickle.dumps({'params': self.params})
                tool.exec_()
