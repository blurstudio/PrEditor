from __future__ import absolute_import, print_function

from Qt.QtCore import QObject, Signal


class Core(QObject):
    """
    The Core class provides all the main shared functionality and signals that need to
    be distributed between different pacakges.
    """

    # ----------------------------------------------------------------
    # blurdev signals
    aboutToClearPaths = Signal()  # Emitted before environment is changed or reloaded

    # ----------------------------------------------------------------

    def __init__(self, objectName=None):
        QObject.__init__(self)
        if objectName is None:
            objectName = 'blurdev'
        QObject.setObjectName(self, objectName)

        # create custom properties
        self._headless = False

        # Paths in this variable will be removed in
        # preditor.osystem.subprocessEnvironment
        self._removeFromPATHEnv = set()

    def shouldReportException(self, exc_type, exc_value, exc_traceback, actions=None):
        """
        Allow core to control how exceptions are handled. Currently being used
        by `BlurExcepthook`, informing which excepthooks should or should not
        be executed.

        Args:
            exc_type (type): exception type class object
            exc_value (Exception): class instance of exception parameter
            exc_traceback (traceback): encapsulation of call stack for exception
            actions (dict, optional): default values for the returned dict. A copy
                of this dict is returned with standard defaults applied.

        Returns:
            dict: Boolean values representing whether to perform excepthook
                action, keyed to the name of the excepthook
        """
        if actions is None:
            actions = {}
        # Create a shallow copy so we don't modify the passed in dict and don't
        # need to use a default value of None
        actions = actions.copy()

        # provide the expected default values
        actions.setdefault('email', True)
        # If blurdev is running headless, there is no way to show a gui prompt
        actions.setdefault('prompt', not self.headless)
        return actions

    @property
    def headless(self):
        """If true, no Qt gui elements should be used because python is running a
        QCoreApplication.
        """
        return self._headless
