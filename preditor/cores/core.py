from __future__ import absolute_import, print_function

from Qt.QtCore import QObject


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to
    be distributed between different pacakges.
    """

    def __init__(self, objectName=None):
        super(Core, self).__init__()
        if objectName is None:
            objectName = 'PrEditor'
        self.setObjectName(objectName)

        # Paths in this variable will be removed in
        # preditor.osystem.subprocessEnvironment
        self._removeFromPATHEnv = set()
