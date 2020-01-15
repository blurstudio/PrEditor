import os
import cPickle

import blurdev

from blurdev.protocols import BaseProtocolHandler


class TreegruntHandler(BaseProtocolHandler):
    name = 'treegrunt'

    def run(self):
        # This is going to take a while, show the splashscreen to
        # entertain the user while they wait for the index to load
        from blurdev.gui.splashscreen import randomSplashScreen

        blurdev.protocolSplash = randomSplashScreen(self.command)

        tool = blurdev.findTool(self.command)
        if not tool.isNull():
            os.environ['BDEV_URL_ARGS'] = cPickle.dumps(self.params)
            tool.exec_()
