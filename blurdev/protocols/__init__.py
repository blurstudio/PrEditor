##
#   :namespace  python.blurdev.protocols
#
#   :remarks    Handlers are classes that process the command and arguments into
#               functioning code.
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       01/12/15
#
from __future__ import print_function
from __future__ import absolute_import


class InvalidHandlerError(Exception):
    """Returned to the pipe if a invalid request was provided"""

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
        """Takes a dict, evals and re-sets all the values and returns the dict."""
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
        """Returns the handler class based off the handler name.

        Loops through BaseProtocolHandler.__subclasses__() and checks if name matches
        and returns the a instance of the first match.

        Args:
            name(str): The name of the handler
            command: The command argument passed to the handler
            params(dict): The params argument passed to the handler
        """
        import pkg_resources

        handlers = pkg_resources.iter_entry_points('blurdev.protocol_handlers')

        for handler in handlers:
            handler_cls = handler.load()
            if handler_cls.name == name:
                return handler_cls(command, params)
        else:
            return cls(command, params)

    def run(self):
        print(self.name, self.command, self.params)
