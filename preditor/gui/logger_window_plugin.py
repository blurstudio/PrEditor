class LoggerWindowPlugin:
    """Base class for LoggerWindow plugins.

    These plugins are loaded using the `preditor.plug.loggerwindow` entry point.
    This entry point is loaded when `LoggerWindow` is initialized. For each entry
    point defined a single instance of the plugin is created per instance of
    a LoggerWindow.

    To save preferences override `record_prefs` and `restore_prefs` methods. These
    are used to save and load preferences any time the PrEditor save/loads prefs.
    """

    def __init__(self, parent):
        self.parent = parent

    def record_prefs(self, name):
        """Returns any prefs to save with the PrEditor's preferences.

        Returns:
            dict: A dictionary that will be saved using json or None.
        """

    def restore_prefs(self, name, prefs):
        """Restore the preferences saved from a previous launch.

        Args:
            name(str): The name specified by the `preditor.plug.loggerwindow`
                entry point.
            prefs(dict or None): The prefs returned by a previous call to
                `record_prefs()` from the last preference save. None is passed
                if no prefs were recorded.
        """
