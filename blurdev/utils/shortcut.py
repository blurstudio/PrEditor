import blurdev as _blurdev

__all__ = [
    'createShortcutBlurIDE',
    'createShortcutPythonLogger',
    'createShortcutTreegrunt',
]


def createShortcutPythonLogger(
    path=None, name='Python Logger', description='Opens the Python Logger.', common=0,
):
    """ Creates a shortcut that launches the Python Logger as a standalone application.

    Args:
        path (str or None, optional): Where to create the shortcut. If None(default) it will
            create the shortcut on the users Desktop.
        name (str, optional): The name of the shortcut. Defaults to 'Python Logger'
        description (str, optional): This text is shown as the comment for the shortcut.
        common (int): If auto generating the path, this controls which desktop the path
            is generated for. 1 is the public shared desktop, while 0(default) is the
            users desktop.
    """
    _blurdev.osystem.createShortcut(
        name,
        _blurdev.runtime('logger.py'),
        path=path,
        icon=_blurdev.resourcePath(r'img\PythonLogger.ico'),
        description=description,
        common=common,
    )


def createShortcutBlurIDE(
    path=None, name='Blur IDE', description='Opens Blur IDE.', common=0
):
    """ Creates a shortcut that launches the Blur IDE as a standalone application.

    Args:
        path (str or None, optional): Where to create the shortcut. If None(default) it will
            create the shortcut on the users Desktop.
        name (str, optional): The name of the shortcut. Defaults to 'Blur IDE'
        description (str, optional): This text is shown as the comment for the shortcut.
        common (int): If auto generating the path, this controls which desktop the path
            is generated for. 1 is the public shared desktop, while 0(default) is the
            users desktop.
    """
    _blurdev.osystem.createShortcut(
        name,
        _blurdev.runtime('ide_editor.py'),
        path=path,
        icon=_blurdev.resourcePath(r'img\ide.ico'),
        description=description,
        common=common,
    )


def createShortcutTreegrunt(
    path=None, name='Treegrunt', description='Opens Treegrunt tool launcher.', common=0,
):
    """ Creates a shortcut that launches Treegrunt as a standalone application.

    Args:
        path (str or None, optional): Where to create the shortcut. If None(default) it will
            create the shortcut on the users Desktop.
        name (str, optional): The name of the shortcut. Defaults to 'Treegrunt'
        description (str, optional): This text is shown as the comment for the shortcut.
        common (int): If auto generating the path, this controls which desktop the path
            is generated for. 1 is the public shared desktop, while 0(default) is the
            users desktop.
    """
    _blurdev.osystem.createShortcut(
        name,
        _blurdev.runtime('treegrunt.py'),
        path=path,
        icon=_blurdev.resourcePath(r'img\treegrunt.ico'),
        description=description,
        common=common,
    )
