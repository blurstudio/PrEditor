##
# 	\namespace	blurdev
#
# 	\remarks	The blurdev package is the core library methods for tools development at Blur Studio
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

__DOCMODE__ = False  # this variable will be set when loading information for documentation purposes

# track the install path
import os, sys
import copy

from PyQt4.QtGui import QMainWindow, QDialog, QVBoxLayout

from blurdev.gui.dialog import Dialog


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


def activeEnvironment():
    """
    Returns the current active Tools Environment as part of the 
    :mod:`blurdev.tools` system.
    
    """
    from blurdev.tools import ToolsEnvironment

    return ToolsEnvironment.activeEnvironment()


def bindMethod(object, name, method):
    """
    Properly binds a new python method to an existing C++ object as a 
    dirty alternative to sub-classing when not possible.
    
    """
    import types

    object.__dict__[name] = types.MethodType(method.im_func, object, object.__class__)


def ensureWindowIsVisible(widget):
    """
    Checks the widget's geometry against all of the system's screens. If it does 
    not intersect it will reposition it to the top left corner of the highest 
    numbered desktop.  Returns a boolean indicating if it had to move the 
    widget.	
    
    """
    from PyQt4.QtGui import QApplication

    desktop = QApplication.desktop()
    geo = widget.geometry()
    for screen in range(desktop.screenCount()):
        monGeo = desktop.screenGeometry(screen)
        if monGeo.intersects(geo):
            break
    else:
        # print 'Resetting %s position, it is offscreen.' % widget.objectName()
        geo.moveTo(monGeo.x() + 7, monGeo.y() + 30)
        # setting the geometry may trigger a second check if setGeometry is overriden
        disable = hasattr(widget, 'checkScreenGeo') and widget.checkScreenGeo
        if disable:
            widget.checkScreenGeo = False
        widget.setGeometry(geo)
        if disable:
            widget.checkScreenGeo = True
        return True
    return False


def findDevelopmentEnvironment():
    from blurdev.tools import ToolsEnvironment

    return ToolsEnvironment.findDevelopmentEnvironment()


def findTool(name, environment=''):
    init()

    from tools import ToolsEnvironment

    if not environment:
        env = ToolsEnvironment.activeEnvironment()
    else:
        env = ToolsEnvironment.findEnvironment(environment)

    if env:
        return env.index().findTool(name)

    from tools.tool import Tool

    return Tool()


def runtime(filepath):
    import os.path

    return os.path.join(installPath, 'runtimes', filepath)


def init():
    pythonw_print_bugfix()
    global core, prefs, application, debug, osystem, settings, tools, enum, XML
    # initialize the settings
    import settings

    settings.init()

    # create the core and application
    if not core:
        # create the core instance
        from blurdev.cores import Core
        import prefs, debug, osystem, settings, tools, enum, XML

        # create the core
        core = Core()

        # initialize the application
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
    :param instance: If subclassed from blurdev.gui.Window or Dialog
                     it will show the existing instance instead of
                     creating a new instance. Ignored if modal == True.
    :param kwargs: A dict of keyword arguments to pass to the widget initialization
    :param wrapClass: launch() requires a dialog or window to work correctly.  If you pass in 
                      a widget, it will automatically get wrapped in a Dialog, unless
                      you specify a class using this argument, in which case it will
                      be wrapped by that.
    """
    global _appHasExec

    init()

    # create the app if necessary
    app = None
    from PyQt4.QtCore import Qt
    from PyQt4.QtGui import QWizard
    from blurdev.cores.core import Core

    if application:
        application.setStyle('Plastique')

        if core.objectName() == 'blurdev':
            core.setObjectName(coreName)

    # always run wizards modally
    iswiz = False
    try:
        iswiz = issubclass(ctor, QWizard)
    except Exception:
        pass

    if iswiz:
        modal = True

    if instance and hasattr(ctor, 'instance') and not modal:
        # use the instance method if requested
        widget = ctor.instance()
    else:
        # show a splash screen if provided
        if splash:
            splash.show()
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
            # blurdev.launch previously had always set to None.
            if args or kwargs:
                if args is None:
                    args = []
                if kwargs is None:
                    kwargs = {}
                widget = ctor(*args, **kwargs)
            else:
                widget = ctor(None)
            return widget

        try:
            widget = launchWidget(ctor, args, kwargs)
        except TypeError:
            # If url arguments are passed in that the tool doesn't accept, remove them.
            widget = launchWidget(ctor, args, oldkwargs)

        if splash:
            splash.finish(widget)

    # If the passed in ctor is not a Dialog or Window, wrap it in a dialog
    # so that it displays correctly.  It will get garbage collected and close
    # otherwise
    if not isinstance(widget, (QMainWindow, QDialog)):
        if wrapClass is not None:
            dlg = wrapClass(None)
        else:
            dlg = Dialog(None)
        layout = QVBoxLayout()
        layout.setMargin(0)
        dlg.setLayout(layout)
        layout.addWidget(widget)
        dlg.setWindowTitle(widget.windowTitle())
        dlg.setWindowIcon(widget.windowIcon())
        widget = dlg

    # check to see if the tool is running modally and return the result
    if modal:
        widget.exec_()
    else:
        widget.show()
        if instance:
            widget.raise_()
            widget.setWindowState(
                widget.windowState() & ~Qt.WindowMinimized | Qt.WindowActive
            )
        # run the application if this item controls it and it hasnt been run before
        if application and not _appHasExec:
            application.setWindowIcon(widget.windowIcon())
            _appHasExec = True
            application.exec_()
    return widget


def quickReload(modulename):
    """
    Searches through the loaded sys modules and looks up matching module names 
    based on the imported module.
    
    """
    import sys, re

    expr = re.compile(str(modulename).replace('.', '\.').replace('*', '[A-Za-z0-9_]*'))

    # reload longer chains first
    keys = sys.modules.keys()
    keys.sort()
    keys.reverse()

    for key in keys:
        module = sys.modules[key]
        if expr.match(key) and module != None:
            print 'reloading', key
            reload(module)


def packageForPath(path):
    import os.path

    path = str(path)
    splt = os.path.normpath(path).split(os.path.sep)
    index = 1

    filename = os.path.join(path, '__init__.py')
    package = []
    while os.path.exists(filename):
        package.append(splt[-index])
        filename = os.path.join(os.path.sep.join(splt[:-index]), '__init__.py')
        index += 1

    package.reverse()
    return '.'.join(package)


def prefPath(relpath, coreName=''):
    # use the core
    if not coreName and core:
        coreName = core.objectName()

    import osystem, os.path

    basepath = os.path.join(
        osystem.expandvars(os.environ['BDEV_PATH_PREFS']), 'app_%s/' % coreName
    )
    return os.path.normpath(os.path.join(basepath, relpath))


def pythonw_print_bugfix():
    """
    Python <=2.4 has a bug where pythonw will silently crash if more than
    4096 bytes are written to sys.stdout.  This avoids that problem by
    redirecting all output to devnull when in Python 2.4 and when using
    pythonw.exe.
    
    """
    if os.path.basename(sys.executable) == 'pythonw.exe':
        if sys.version_info[:2] <= (2, 4):
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')


def registerScriptPath(filename):
    from tools import ToolsEnvironment

    ToolsEnvironment.registerScriptPath(filename)


def relativePath(path, additional):
    """
    Replaces the last element in the path with the passed in additional path.
    :param path: Source path. Generally a file name.
    :param additional: Additional folder/file path appended to the path.
    :return str: The modified path
    """
    import os.path

    return os.path.join(os.path.split(str(path))[0], additional)


def resetWindowPos():
    """
        Reset any top level widgets(windows) to 0,0 use this to find windows that are offscreen.
    """
    from PyQt4.QtGui import QApplication

    for widget in QApplication.instance().topLevelWidgets():
        if widget.isVisible():
            geo = widget.geometry()
            width = geo.width()
            height = geo.height()
            geo.setX(8)
            geo.setY(30)
            geo.setWidth(width)
            geo.setHeight(height)
            widget.setGeometry(geo)


def resourcePath(relpath):
    """
    Returns the full path to the file inside the blurdev\resource folder
    :param relpath: The additional path added to the blurdev\resource folder path.
    :return str: The modified path
    """
    return relativePath(__file__, 'resource/%s' % relpath)


def runTool(toolId, macro=""):
    init()

    from PyQt4.QtGui import QApplication
    from tools import ToolsEnvironment

    # load the tool
    tool = ToolsEnvironment.activeEnvironment().index().findTool(toolId)
    if not tool.isNull():
        tool.exec_(macro)

    # let the user know the tool could not be found
    elif QApplication.instance():
        from PyQt4.QtGui import QMessageBox

        QMessageBox.critical(
            None,
            'Tool Not Found',
            '%s is not a tool in %s environment.'
            % (toolId, ToolsEnvironment.activeEnvironment().objectName()),
        )


def setActiveEnvironment(env):
    from blurdev.tools import ToolsEnvironment

    return ToolsEnvironment.findEnvironment(env).setActive()


def setAppUserModelID(id, prefix='Blur'):
    """
    Specifies a Explicit App User Model ID that Windows 7 uses to control
    grouping of windows on the taskbar.  This must be set before any ui 
    is displayed. The best place to call it is in the first widget to 
    be displayed __init__ method.
    
    :param id: the id of the application.  Should use full camel-case.
               `http://msdn.microsoft.com/en-us/library/dd378459%28v=vs.85%29.aspx#how`_
    :param prefix: The prefix attached to the id.  For a blur tool called
                   fooBar, the associated appId should be *Blur.FooBar*.  
                   Defaults to *Blur*.
    """
    try:
        import blur.Stone
    except:
        return False
    if hasattr(blur.Stone, 'qSetCurrentProcessExplicitAppUserModelID'):
        blur.Stone.qSetCurrentProcessExplicitAppUserModelID('%s.%s' % (prefix, id))
        return True
    return False


def signalInspector(item, prefix='----', ignore=[]):
    """
    Connects to all signals of the provided item, and prints the name of 
    each signal.  When that signal is activated it will print the prefix, 
    the name of the signal, and any arguments passed. These connections 
    will persist for the life of the object.
    
    :param item: QObject to inspect signals on.
    :type item: :class:`PyQt4.QtCore.QObject`
    :param prefix: The prefix to display when a signal is emitted.
    :param ignore: A list of signal names to ignore
    :type ignore: list

    """

    def create(attr):
        def handler(*args, **kwargs):
            print prefix, 'Signal:', attr, 'ARGS:', args, kwargs

        return handler

    for attr in dir(item):
        if (
            type(getattr(item, attr)).__name__ == 'pyqtBoundSignal'
            and not attr in ignore
        ):
            print attr
            getattr(item, attr).connect(create(attr))


def startProgress(title='Progress', parent=None):
    from blurdev.gui.dialogs.multiprogressdialog import MultiProgressDialog

    return MultiProgressDialog.start(title)


# track the install path
installPath = os.path.split(__file__)[0]
"""Stores the full filepath of the blurdev installation directory."""

# initialize the core
init()
# add the blurdev version info to the error email
import version

os.environ['BDEV_EMAILINFO_BLURDEV_VERSION'] = version.toString()
