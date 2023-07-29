from __future__ import absolute_import

import json
import logging
import logging.config
import os

from .prefs import prefs_path


class LoggingConfig(object):
    def __init__(self, core_name, version=1):
        self._filename = None
        self.cfg = {'version': version}
        self.core_name = core_name

    def add_logger(self, name, logger):
        if not logger.level:
            # No need to record a logger that is inheriting its logging level
            return

        # Build the required dictionaries
        loggers = self.cfg.setdefault('loggers', {})
        log = loggers.setdefault(name, {})
        log['level'] = logger.level

    def build(self):
        self.add_logger("", logging.root)
        for name, logger in logging.root.manager.loggerDict.items():
            if not isinstance(logger, logging.PlaceHolder):
                self.add_logger(name, logger)

    @property
    def filename(self):
        if self._filename:
            return self._filename

        self._filename = prefs_path('logging_prefs.json', core_name=self.core_name)
        return self._filename

    def load(self):
        if not os.path.exists(self.filename):
            return False

        with open(self.filename) as fle:
            self.cfg = json.load(fle)
            logging.config.dictConfig(self.cfg)
        return True

    def save(self):
        with open(self.filename, 'w') as fle:
            json.dump(self.cfg, fle, indent=4)
