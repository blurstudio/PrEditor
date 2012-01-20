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
import os, sys, types

application = None  # create a managed QApplication
core = None  # create a managed Core instance


def activeEnvironment():
    from blurdev.tools import ToolsEnvironment

    return ToolsEnvironment.activeEnvironment()


def bindMethod(object, name, method):
    """ Properly binds a new python method to an existing C++ object as a dirty alternative to sub-classing when not possible """
    object.__dict__[name] = types.MethodType(method.im_func, object, object.__class__)


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
    global core, prefs, application, debug, osystem, settings, tools, enum
    # initialize the settings
    import settings

    settings.init()

    # create the core and application
    if not core:
        # create the core instance
        from blurdev.cores import Core
        import prefs, debug, osystem, settings, tools, enum

        # create the core
        core = Core()

        # initialize the application
        application = core.init()


def launch(ctor, modal=False, coreName='external'):
    """
        \remarks	This method is used to create an instance of a widget (dialog/window) to be run inside
                    the blurdev system.  Using this function call, blurdev will determine what the application is
                    and how the window should be instantiated, this way if a tool is run as a standalone, a
                    new application instance will be created, otherwise it will run on top of a currently
                    running application.

        \param		ctor		QWidget || method 	(constructor for a widget, most commonly a Dialog/Window/Wizard>
        \param		modal		<bool>	whether or not the system should run modally
        \param		coreName	<str>	string to give to the core if the application is going to be rooted under this widget

        \return		<bool>	success (when exec_ keyword is set) || <ctor> instance (when exec_ keyword is not set)
    """
    init()

    # create the app if necessary
    app = None
    from PyQt4.QtGui import QWizard
    from blurdev.cores.core import Core

    # setAppUserModelID(coreName)

    if application:
        application.setStyle('Plastique')

        if core.objectName() == 'blurdev':
            core.setObjectName(coreName)

    # always run wizards modally
    iswiz = False
    try:
        iswiz = issubclass(ctor, QWizard)
    except:
        pass

    if iswiz:
        modal = True

    # create the output instance from the class
    widget = ctor(None)

    # check to see if the tool is running modally and return the result
    if modal:
        return widget.exec_()
    else:
        widget.show()
        # run the application if this item controls it
        if application:
            application.setWindowIcon(widget.windowIcon())
            application.exec_()
        return widget


def quickReload(modulename):
    """
        \remarks	searches through the loaded sys modules and looks up matching module names based on the imported module
        \param		modulename 	<str>
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
    """Python <=2.4 has a bug where pythonw will silently crash if more than
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
    return relativePath(__file__, 'resource/%s' % relpath)


def runTool(toolId, macro=""):
    init()

    # special case scenario - treegrunt
    if toolId == 'Treegrunt':
        core.showTreegrunt()

    # otherwise, run the tool like normal
    else:
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
        \remarks	Specifies a Explicit App User Model ID that Windows 7 uses to controll grouping of windows on the taskbar.
                    This must be set before any ui is displayed. The best place to call it is in the first widget to be displayed __init__ method.
        \param		id	<str>	The id of the application. Should use full camel-case. http://msdn.microsoft.com/en-us/library/dd378459%28v=vs.85%29.aspx#how
        \param		prefix	<str>	The prefix attached to the id. For a blur tool called fooBar, the associated appid should be Blur.FooBar
                    
                    To set the window's icon: widget.setWindowIcon(QIcon('img/icon.png'))
    """
    try:
        import blur.Stone
    except:
        return False
    if hasattr(blur.Stone, 'qSetCurrentProcessExplicitAppUserModelID'):
        blur.Stone.qSetCurrentProcessExplicitAppUserModelID('%s.%s' % (prefix, id))
        return True
    return False


def signalInspector(item, prefix='----'):
    """
        \Remarks	Connects to all signals of the provided item, and prints the name of each signal. 
                    When that signal is activated it will print the prefix, the name of the signal, 
                    and any arguments passed. These connections will persist for the life of the object.
        \param		item	<QObject>	Listen for signals from this object.
        \param		prefix	<str>		The prefix it displays when a signal is emited. Defaults to '----'	
    """

    def create(attr):
        def handler(*args, **kwargs):
            print prefix, 'Signal:', attr, 'ARGS:', args, kwargs

        return handler

    for attr in dir(item):
        if type(getattr(item, attr)).__name__ == 'pyqtBoundSignal':
            print attr
            getattr(item, attr).connect(create(attr))


def startProgress(title='Progress', parent=None):
    from blurdev.gui.dialogs.multiprogressdialog import MultiProgressDialog

    return MultiProgressDialog.start(title)


def synthesize(object, name, value):
    """
        \Remarks	Convenience method to create getters and setters for a instance. Should be called
                    from within __init__. Creates [name], set[Name], _[name] on object.
        \param		object	<instance>	An instance of the class to add the methods to
        \param		name	<str>		The base name to build the function names, and storage variable
        \param		value	<object>	The inital state of the created variables
    """
    storageName = '_%s' % name
    setterName = 'set%s%s' % (name[0].capitalize(), name[1:])
    if hasattr(object, name):
        raise KeyError('The provided name already exists')
    # add the storeage variable to the object
    setattr(object, storageName, value)
    # define the getter
    def customGetter(self):
        return getattr(self, storageName)

    # define the Setter
    def customSetter(self, state):
        setattr(self, storageName, state)

    # add the getter to the object, if it does not exist
    if not hasattr(object, name):
        setattr(object, name, types.MethodType(customGetter, object))
    # add the setter to the object, if it does not exist
    if not hasattr(object, setterName):
        setattr(object, setterName, types.MethodType(customSetter, object))


# track the install path
installPath = os.path.split(__file__)[0]

# initialize the core
init()
