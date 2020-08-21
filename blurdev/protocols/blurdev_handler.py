import blurdev

from blurdev.protocols import BaseProtocolHandler


class BlurdevHandler(BaseProtocolHandler):
    """ Used to run specific blurdev commands.

    Can be used to show the logger and treegrunt. If you use the TreegruntHandler to
    show the logger in the external treegrunt, it will launch a new python process for
    the logger, which is not what we want to happen.
    """

    name = 'blurdev'

    def run(self):
        if self.command == 'showLogger':
            blurdev.core.showLogger()
        elif self.command == 'showTreegrunt':
            blurdev.core.showTreegrunt()
