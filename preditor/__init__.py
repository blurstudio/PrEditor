from __future__ import absolute_import
from __future__ import print_function

# Override the base logging class.
from . import logger

logger.patchLogger()

# this variable will be set when loading information for documentation purposes
__DOCMODE__ = False

# track the install path
import os  # noqa: E402
import sys  # noqa: E402
import copy  # noqa: E402
import logging  # noqa: E402
import weakref  # noqa: E402

from Qt.QtWidgets import (  # noqa: E402
    QDialog,
    QDockWidget,
    QMainWindow,
    QVBoxLayout,
)
from Qt.QtCore import Qt  # noqa: E402

from .version import version as __version__  # noqa: E402,F401
from . import settings, osystem  # noqa: E402

application = None  # create a managed QApplication
_appHasExec = False
"""
The blurdev managed QApplication returned from :meth:`Core.init` as part
of the :mod:`blurdev.cores` system.
"""

core = None  # create a managed Core instance
"""
The blurdev managed :class:`Core` object from the :mod:`blurdev.cores` module.
"""
# Weakref.ref does not accept None, and None is not callable. Passing the lambda
# ensures the same functionality even if no tool has been launched yet.
lastLaunched = weakref.ref(lambda: None)
"""
This is set any time blurdev.launch is called. It contains the Dialog or Window
object. This is for debugging, and there is no guarantee that the object has not
been deleted.
"""

# To show a splashscreen as soon as possible, the blurdev.protocols system
# may store a splashscreen here. This will be None unless the protocol
# system sets it, and it will be cleared the first time blurdev.launch
# is called. blurdev.gui.splashscreen.randomSplashScreen checks this value
protocolSplash = None

# Create the root blurdev module logging object.
_logger = logging.getLogger(__name__)

# Add a NullHandler to suppress the "No handlers could be found for _logger"
# warnings from being printed to stderr. Studiomax and possibly other DCC's
# tend to treat any text written to stderr as a error when running headless.
# We also don't want this warning showing up in production anyway.
_logger.addHandler(logging.NullHandler())


def appUserModelID():
    """Returns the current Windows 7+ app user model id used for taskbar grouping."""
    import ctypes
    from ctypes import wintypes

    lpBuffer = wintypes.LPWSTR()
    AppUserModelID = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID
    AppUserModelID(ctypes.cast(ctypes.byref(lpBuffer), wintypes.LPWSTR))
    appid = lpBuffer.value
    ctypes.windll.kernel32.LocalFree(lpBuffer)
    return appid


def init():
    os.environ['BDEV_EMAILINFO_PREDITOR_VERSION'] = __version__
    pythonw_print_bugfix()
    settings.init()
    global core, application
    # create the core and application
    if not core:
        from .cores import Core

        objectName = None
        _exe = os.path.basename(sys.executable).lower()
        # Treat designer as a seperate core so it gets its own prefrences.
        if 'designer' in _exe:
            objectName = 'designer'
        elif 'assfreezer' in _exe:
            objectName = 'assfreezer'
        core = Core(objectName=objectName)
        application = core.init()


def launch(
    ctor,
    modal=False,
    coreName='external',
    instance=False,
    args=None,
    kwargs=None,
    splash=None,
    wrapClass=None,
    dockWidgetArea=Qt.RightDockWidgetArea,
):
    """
    This method is used to create an instance of a widget (dialog/window) to
    be run inside the blurdev system.  Using this function call, blurdev will
    determine what the application is and how the window should be
    instantiated, this way if a tool is run as a standalone, a new
    application instance will be created, otherwise it will run on top
    of a currently running application.

    :param ctor: callable object that will return a widget instance, usually
                 a :class:`QWidget` or :class:`QDialog` or a function that
                 returns an instance of one.
    :param modal: If True, widget will be created as a modal widget (ie. blocks
                  access to calling gui elements).
    :param coreName: string to give to the core if the application is
                     going to be rooted under this widget
    :param instance: If subclassed from preditor.gui.Window or Dialog
                     it will show the existing instance instead of
                     creating a new instance. Ignored if modal == True.
    :param kwargs: A dict of keyword arguments to pass to the widget initialization
    :param wrapClass: launch() requires a subclass of QDialog, QMainWindow or DockWidget
        to work correctly. If you pass in a widget, it will automatically get wrapped in
        a Dialog, unless you specify a class using this argument, in which case it will
        be wrapped by that.
    :param dockWidgetArea: If ctor is a QDockWidget
    """
    global lastLaunched
    global protocolSplash

    if application:
        application.setStyle(core.defaultStyle())

    if instance and hasattr(ctor, 'instance') and not modal:
        # use the instance method if requested
        widget = ctor.instance()
    else:
        # Handle any url arguments that were passed in using the environment.
        urlArgs = os.environ.pop('BDEV_URL_ARGS', None)
        oldkwargs = copy.copy(kwargs)
        if urlArgs:
            import cPickle

            urlArgs = cPickle.loads(urlArgs)
            if kwargs is None:
                kwargs = urlArgs
            else:
                kwargs.update(urlArgs)

        def launchWidget(ctor, args, kwargs):
            # create the output instance from the class
            # If args or kwargs are defined, use those.  NOTE that if you pass any
            # args or kwargs, you will also have to supply the parent, which
            # preditor.launch previously had always set to None.
            if args or kwargs:
                if args is None:
                    args = []
                if kwargs is None:
                    kwargs = {}
                widget = ctor(*args, **kwargs)
            else:
                global core
                widget = ctor(core.rootWindow())
            return widget

        try:
            widget = launchWidget(ctor, args, kwargs)
        except TypeError:
            # If url arguments are passed in that the tool doesn't accept, remove them.
            widget = launchWidget(ctor, args, oldkwargs)

    # Attach the protocolSplash.finish to the widget we are creating and
    # remove the reference so we don't keep using it.
    if protocolSplash is not None:
        protocolSplash.finish(widget)
        protocolSplash = None

    if splash:
        splash.finish(widget)

    # If the passed in ctor is not a QDialog, QMainWindow or QDockWidget, wrap it in a
    # dialog so that it displays correctly. It will get garbage collected and close
    # otherwise
    if not isinstance(widget, (QMainWindow, QDialog, QDockWidget)):
        if wrapClass is not None:
            dlg = wrapClass(None)
        else:
            from .gui.dialog import Dialog

            dlg = Dialog(None)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        dlg.setLayout(layout)
        layout.addWidget(widget)
        dlg.setWindowTitle(widget.windowTitle())
        dlg.setWindowIcon(widget.windowIcon())
        widget = dlg

    # Store the last launched tool so a developer can easily find it to experiment with.
    lastLaunched = weakref.ref(widget)
    # check to see if the tool is running modally and return the result
    if modal:
        widget.exec_()
    else:
        if isinstance(widget, QDockWidget) and widget.parent() and dockWidgetArea:
            widget.parent().addDockWidget(dockWidgetArea, widget)
        widget.show()
        if instance:
            widget.raise_()
            widget.setWindowState(
                widget.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
            )
        # run the application if this item controls it and it hasnt been run before
        startApplication(widget.windowIcon())
    return widget


def startApplication(windowIcon=None):
    """Starts preditor.application if it hasn't already been started."""
    global _appHasExec
    if application and not _appHasExec:
        if windowIcon:
            application.setWindowIcon(windowIcon)
        _appHasExec = True
        application.exec_()


def prefPath(relpath, coreName=''):
    # use the core
    if not coreName and core:
        coreName = core.objectName()
    basepath = os.path.join(
        osystem.expandvars(os.environ['BDEV_PATH_PREFS']), 'app_%s/' % coreName
    )
    return os.path.normpath(os.path.join(basepath, relpath))


def pythonw_print_bugfix():
    """
    When running pythonw print statements and file handles tend to have problems
    so, if its pythonw and stderr and stdout haven't been redirected, redirect them
    to os.devnull.
    """
    if os.path.basename(sys.executable) == 'pythonw.exe':
        if sys.stdout == sys.__stdout__:
            sys.stdout = open(os.devnull, 'w')
        if sys.stderr == sys.__stderr__:
            sys.stderr = open(os.devnull, 'w')


def relativePath(path, additional=''):
    """
    Replaces the last element in the path with the passed in additional path.
    :param path: Source path. Generally a file name.
    :param additional: Additional folder/file path appended to the path.
    :return str: The modified path
    """
    return os.path.join(os.path.dirname(path), additional)


def resourcePath(relpath=''):
    """Returns the full path to the file inside the preditor/resource folder

    Args:
        relpath (str, optional): The additional path added to the
            preditor/resource folder path.
    
    Returns:
        str: The modified path
    """
    return os.path.join(relativePath(__file__), 'resource', relpath)


def setAppUserModelID(appId, prefix='Blur'):
    """Controls Windows taskbar grouping.

    Specifies a Explicit App User Model ID that Windows 7+ uses to control grouping of
    windows on the taskbar.  This must be set before any ui is displayed. The best place
    to call it is in the first widget to be displayed __init__ method.

    See :py:meth:`preditor.osystem.set_app_id_for_shortcut` to set the app id on a
    windows shortcut.

    Args:
        appId (str): The id of the application. Should use full camel-case.
            `http://msdn.microsoft.com/en-us/library/dd378459%28v=vs.85%29.aspx#how`_

        prefix (str, optional): The prefix attached to the id.  For a blur tool called
            fooBar, the associated appId should be "Blur.FooBar". Defaults to "Blur".
    """

    if settings.OS_TYPE != 'Windows':
        return False

    # If this function is run inside other applications, it can cause(unparented) new
    # sub windows to parent with this id instead of the parent application in windows.
    # To test: Create a window calling setAppUserModelID before showing it. Use a unique
    # appId. Then create a unparented window and show it. The unparented window will
    # appear in a different taskbar group.
    if not core.useAppUserModelID():
        return False

    # https://stackoverflow.com/a/27872625
    import ctypes

    myappid = u'%s.%s' % (prefix, appId)
    return not ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


def signalInspector(item, prefix='----', ignore=None):
    """Connects to all signals of the provided item, and prints the name of
    each signal.  When that signal is activated it will print the prefix,
    the name of the signal, and any arguments passed. These connections
    will persist for the life of the object.

    Args:
        item (Qt.QtCore.QObject): QObject to inspect signals on.
        prefix (str, optional): The prefix to display when a signal is emitted.
        ignore (list, optional): A list of signal names to ignore
    """

    def create(attr):
        def handler(*args, **kwargs):
            print(prefix, 'Signal:', attr, 'ARGS:', args, kwargs)

        return handler

    if ignore is None:
        ignore = []

    for attr in dir(item):
        if (
            type(getattr(item, attr)).__name__ == 'pyqtBoundSignal'
            and attr not in ignore
        ):
            print(attr)
            getattr(item, attr).connect(create(attr))


# initialize the core
init()
