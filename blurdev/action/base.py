import inspect
import os.path
import sys

from .constants import *
from .exceptions import *

# =============================================================================
# CLASSES
# =============================================================================


class Action(object):
    """An abstract base class that is the core of the action framework.  All
    concrete actions are derived from this class.
    """

    def __new__(cls, *args, **kwargs):
        if cls is Action:
            raise NotImplementedError(
                'The Action class may only be used as a base class.'
            )
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """Initializes a new Action.

        During initialization of the action, various routines are performed.
        The various hooks defined by the action are identified and registered
        with the `Action`, arguments are parsed, type checked, and defaulted
        where necessary, and child actions are registered.

        Args:
            argRename(dict): A mapping of input argument names to keyword
                arguments of this action.  This allows a parent action to rename
                the arguments of this action, and this action to understand that
                new mapping and properly understand given kwargs and assign the
                values of those to the correct attributes of this action.  This
                argument must be provided as a keyword argument.

            childrenFirst(bool): Causes child actions to be executed before
                this action's execute hook. This argument must be provided as
                a keyword argument.  Default is False.

        Returns:
            N/A

        Raises:
            NotImplementedError: The action has an execute hook, but one is
                not defined for the current application context (ie: Maya, Max, etc)
            ArgumentRequiredButNotGivenError: A required argument for the action
                was not provided
            TypeError: A value was given that was not of the correct type.  This
                is raised if a child action is provided that is not of class `Action`
                or if an argument value was given that is not of the correct type
                as defined by the argument definition for the action.
        """
        self._currentApplication = None
        self.setApplicationContext()
        self._preChildHooks = []
        self._postChildHooks = []
        self._enterHook = None
        self._exitHook = None
        self._executeHook = None
        self._preExecuteHooks = []
        self._postExecuteHooks = []
        self._childrenFirst = bool(kwargs.get('childrenFirst', False))
        self._childActions = []
        # This will be used to determine whether any execute has been
        # defined for the action.  This will give us the ability to know
        # whether an execute hook has been defined for some application
        # context, even if our current context is not supported.  That
        # will then allow us know whether this action is usable in the
        # current application context.
        self._hasExecuteHook = False
        self._hasContextHooks = False
        # Rather than use args and kwargs directly we need to store
        # them so that they can be updated and passed on in the event
        # of any argument renames requested by this action or any that
        # might be doing the same thing deeper in the tree.  This is
        # explained in more depth below in setArguments().
        self._args = args
        self._kwargs = kwargs
        self._setArguments(dict(kwargs.get('argRename', dict())))
        self._registerHooks()
        # After hooks are registered, we can determine whether the action
        # is implemented for some application context, but NOT implemented
        # for our current application context.
        if self._hasExecuteHook and not self._executeHook:
            raise NotImplementedError(
                'Action {0} has not been implemented for application: {1}'.format(
                    str(self), str(self._currentApplication),
                )
            )
        self._registerChildActions(*self._args, **self._kwargs)
        self._registerApplicationMethods()
        self._sortHooks()

    @property
    def currentApplication(self):
        """The current application context as an App Enum."""
        return self._currentApplication

    @property
    def childActions(self):
        """The action's child actions."""
        return self._childActions

    def addChildActions(self, children):
        """Adds an `Action` to this action's list of child actions.

        Args:
            children(list): A list of child actions to add to the action.

        Returns:
            N/A

        Raises:
            TypeError: A child action was given that is not of class `Action`.
        """
        if [c for c in list(children) if not isinstance(c, Action)]:
            raise TypeError('Child actions must be of type Action.')
        self._childActions.extend(list(children))

    def addPostExecuteHooks(self, hooks):
        """Adds to the list of post-execute hooks.

        Args:
            hooks(list): A list of callables to add as post-execute hooks.

        Returns:
            N/A

        Raises:
            N/A
        """
        self._postExecuteHooks.extend(list(hooks))

    def addPreExecuteHooks(self, hooks):
        """Adds to the list of pre-execute hooks.

        Args:
            hooks(list): A list of callables to add as pre-execute hooks.

        Returns:
            N/A

        Raises:
            N/A
        """
        self._preExecuteHooks.extend(list(hooks))

    def setApplicationContext(self, registerHooks=False):
        """Detects and sets the current application context.

        Looks to sys.executable to determine what application the action
        currently is running within (like 3ds Max, or Maya, etc).  After
        determining the current context, any application-specific imports
        that have been registered with the action via applicationimporter
        methods will be run.

        Args:
            registerHooks(bool): Force re-registration of all hooks.

        Returns:
            N/A

        Raises:
            N/A
        """
        _exe = os.path.basename(sys.executable).lower()
        if 'maya' in _exe:
            self._currentApplication = Apps.Maya
        elif 'motionbuilder' in _exe:
            self._currentApplicationn = Apps.MotionBuilder
        elif 'max' in _exe:
            self._currentApplication = Apps.Max
        elif 'xsi' in _exe:
            self._currentApplication = Apps.XSI
        else:
            self._currentApplication = Apps.External
        mLocals = self._runApplicationImports()
        if mLocals:
            globals().update(mLocals)
        if registerHooks:
            self._registerHooks()
            self._registerApplicationMethods()
            self._sortHooks()

    def _executePreChildHooks(self, childAction):
        for preChildHook in self._preChildHooks:
            preChildHook(childAction)

    def _executePostChildHooks(self, childAction):
        for postChildHook in self._postChildHooks:
            postChildHook(childAction)

    def _executePreExecuteHooks(self):
        for preHook in self._preExecuteHooks:
            preHook()

    def _executePostExecuteHooks(self):
        for postHook in self._postExecuteHooks:
            postHook()

    def _execute(self, *args, **kwargs):
        self._executePreExecuteHooks()
        if self._childrenFirst:
            self._executeChildren()
        executeHook = self._executeHook
        if executeHook:
            ret = executeHook(*args, **kwargs)
        else:
            ret = None
        if not self._childrenFirst:
            self._executeChildren()
        self._executePostExecuteHooks()
        return ret

    def _executeChildren(self):
        for childAction in self._childActions:
            self._executePreChildHooks(childAction)
            childAction()
            self._executePostChildHooks(childAction)

    def _registerApplicationMethods(self):
        # We're registering application-specific methods here,
        # and while doing so we will also set things up so that if
        # a method is called that is implemented for some application,
        # but NOT for our current application context that an exception
        # is raised if that method is called.
        appMethods = dict()
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except AttributeError:
                continue
            if not inspect.ismethod(method):
                continue
            elif hasattr(method, '_applicationmethod__appMethodName'):
                supportedApp = getattr(method, '_applicationmethod__appMethodApp')
                currentApp = self.currentApplication
                mName = getattr(method, '_applicationmethod__appMethodName')
                if supportedApp == Apps.All or supportedApp == currentApp:
                    appMethods[mName] = method
                elif mName not in appMethods:
                    appMethods[mName] = self._unimplementedApplicationMethod
        for mName, method in appMethods.iteritems():
            setattr(self, mName, method)

    def _registerChildActions(self, *args, **kwargs):
        childActions = []
        # Child action definitions are stored as methods with an extra
        # bit of data in the form of a container object that records
        # the information necessary to instantiate the child action.
        # We look for the tag, pull the container, instantiate the child
        # action object, and then store it.
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except AttributeError:
                continue
            if not inspect.ismethod(method):
                continue
            elif hasattr(method, '_childaction__container'):
                childActions.append(getattr(method, '_childaction__container'))
        if not childActions:
            return
        childActions = sorted(childActions, key=lambda c: c._childaction__order,)
        for container in childActions:
            cls = container.childClass
            childAction = cls(container.argRename, *args, **kwargs)
            setattr(self, container.name, childAction)
            self._childActions.append(childAction)

    def _registerHooks(self):
        # Hooks are methods tagged with an identifying attribute.  We
        # identify the tag and set out property for that hook to be the
        # tagged method.
        currentApp = self.currentApplication
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except AttributeError:
                continue
            if not inspect.ismethod(method):
                continue
            elif hasattr(method, '_prechildhook__actionPreChildHook'):
                supportedApp = method._prechildhook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._preChildHooks.append(method)
            elif hasattr(method, '_postchildhook__actionPostChildHook'):
                supportedApp = method._postchildhook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._postChildHooks.append(method)
            elif hasattr(method, '_executehook__actionExecuteHook'):
                # Regardless of whether we have an execute hook defined
                # for the current application, we need to record that we
                # have some execute hook defined.  This will allow us to
                # know whether the action is implemented for some application
                # other than our current context, but possible not for our
                # current context.
                self._hasExecuteHook = True
                supportedApp = method._executehook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._executeHook = method
            elif hasattr(method, '_preexecutehook__actionPreExecuteHook'):
                supportedApp = method._preexecutehook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._preExecuteHooks.append(method)
            elif hasattr(method, '_postexecutehook__actionPostExecuteHook'):
                supportedApp = method._postexecutehook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._postExecuteHooks.append(method)
            elif hasattr(method, '_enterhook__actionEnterHook'):
                self._hasContextHooks = True
                supportedApp = method._enterhook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._enterHook = method
            elif hasattr(method, '_exithook__actionExitHook'):
                self._hasContextHooks = True
                supportedApp = method._exithook__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    self._exitHook = method

    def _runApplicationImports(self):
        currentApp = self.currentApplication
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except AttributeError:
                continue
            if not inspect.ismethod(method):
                continue
            elif hasattr(method, '_applicationimporter__actionAppImporter'):
                supportedApp = method._applicationimporter__supportedApp
                if supportedApp == Apps.All or supportedApp == currentApp:
                    method()
                    mLocals = method._locals
                    updates = dict()
                    # We need to see what modules and/or classes were imported
                    # in the importer method.  Collect a list of all modules
                    # registered to sys.modules and return those.
                    for key, value in mLocals.iteritems():
                        if inspect.ismodule(value) or inspect.isclass(value):
                            if key == 'cls' or key == 'self':
                                continue
                            updates[key] = value
                    return updates
        return dict()

    def _setArguments(self, argRename=dict()):
        args = self._args
        kwargs = self._kwargs
        arguments = []
        # Each one of the argument methods will have an attribute
        # labeling it as such.  That attribute will contain the
        # argument object that defines name of the argument along
        # with a place to store its value and a bit to mark it as
        # having been found.  First we need to find those argument
        # objects.
        argumentMethods = []
        for attr in dir(self):
            try:
                method = getattr(self, attr)
            except AttributeError:
                continue
            if not inspect.ismethod(method):
                continue
            elif hasattr(method, '_argproperty__actionArgument'):
                argumentMethods.append(method)
        # Sort the arguments in the order that they were defined in the
        # class.  This will ensure that if ordered arguments are provided
        # when the action is instantiated that they may be given in the
        # argument definition order of the action.
        argumentMethods = sorted(argumentMethods, key=lambda a: a._argproperty__order,)
        for method in argumentMethods:
            arguments.append(getattr(method, '_argproperty__actionArgument'))
        # Now that we have our argument objects we can process each
        # one.  The way we do this is to first look for positional
        # arguments and if they were given we index into that list
        # and pull them out in order until we're beyond the length
        # of the argument list.  If we don't find our argument value
        # in the positionals or we have stepped beyond its length we
        # then look in the keyword arguments to see if we can find
        # it there.  This is where argument renaming comes into play.
        # What we have to do is look to see if the argument we're
        # processing has a rename request and if so look for the
        # target name of the rename for the argument in kwargs and use
        # that value if found.  If we did find the renamed argument
        # we record that value as normal, mark the argument as found,
        # and then update the kwargs dictionary to point the original
        # argument name to the value of the rename.  This will allow
        # any child actions that also have argument renames to find
        # the appropriate value as we're spiralling down the action
        # hierarchy.
        i = 0
        for argument in arguments:
            if args:
                try:
                    argument.value = args[i]
                except IndexError:
                    pass
                else:
                    argument.found = True
                i = i + 1
            if not argument.found:
                if argument.name in argRename:
                    argName = argRename(argument.name)
                else:
                    argName = argument.name
                if argName in kwargs:
                    argument.value = kwargs.get(argName)
                    kwargs[argument.name] = argument.value
                    argument.found = True
                else:
                    # If we found nothing, see if there's been a default
                    # given and use that.  If there wasn't then there's a
                    # required argument that was not given and we need to
                    # raise an exception.
                    try:
                        argument.value = kwargs.get(argument.name, argument.default)
                        argument.found = True
                    except ArgumentHasNoDefaultError:
                        msg = 'Required argument {name} was not given.'.format(
                            name=argument.name,
                        )
                        raise ArgumentRequiredButNotGivenError(msg)
        # Argument renames might have caused args and kwargs to now have
        # extra stuff, so we'll keep track of that.
        self._args = args
        self._kwargs = kwargs
        argumentsNotFound = [a.name for a in arguments if not a.found]
        if argumentsNotFound:
            msg = 'Required arguments {names} were not given.'.format(
                names=', '.join(argumentsNotFound),
            )
            raise ArgumentRequiredButNotGivenError(msg)
        else:
            # Since we're certain we have all of our arguments now, we
            # can set the properties on the action so that those values
            # are easily accessible.
            for argument in arguments:
                ad = _PropertyDescriptor(
                    name=argument.name,
                    value=argument.value,
                    atype=argument.atype,
                    valid=argument.validValues,
                    settable=argument.settable,
                )
                setattr(
                    self, argument.propertyName, ad,
                )
        for argument in arguments:
            argument.__del__()

    def _sortHooks(self):
        # The order that each hook was defined is stored as an attribute
        # on the function itself.  We just have to sort based on that
        # order and we're good to go.  This will ensure that the order
        # that the hooks are defined in the action is the order that they
        # are executed.  This is only a concern for hook types that
        # support multiple definitions, so things like executehook,
        # enterhook, and exithook are of no concern since there is only
        # one of each allowed.
        if self._preChildHooks:
            self._preChildHooks = sorted(
                self._preChildHooks, key=lambda h: h._prechildhook__order,
            )
        if self._postChildHooks:
            self._postChildHooks = sorted(
                self._postChildHooks, key=lambda h: h._postchildhook__order,
            )
        if self._preExecuteHooks:
            self._preExecuteHooks = sorted(
                self._preExecuteHooks, key=lambda h: h._preexecutehook__order,
            )
        if self._postExecuteHooks:
            self._postExecuteHooks = sorted(
                self._postExecuteHooks, key=lambda h: h._postexecutehook__order,
            )

    def _unimplementedApplicationMethod(self, *args, **kwargs):
        raise NotImplementedError(
            'Method is not implemented for application {}'.format(
                str(self.currentApplication),
            )
        )

    def __call__(self, *args, **kwargs):
        return self._execute(*args, **kwargs)

    def __enter__(self):
        if not self._enterHook and not self._exitHook:
            if self._hasContextHooks:
                msg = 'No "{0}" support for context manager {1}'.format(
                    str(self.currentApplication), str(self),
                )
            else:
                msg = 'Action {} is not implemented as a context manager.'.format(
                    str(self),
                )
            raise NotImplementedError(msg)
        if self._enterHook:
            self._enterHook()
        return self

    def __exit__(self, *args, **kwargs):
        if self._exitHook:
            self._exitHook(*args, **kwargs)

    def __getattribute__(self, key):
        value = super(Action, self).__getattribute__(key)
        if isinstance(value, _PropertyDescriptor):
            return value.getValue()
        else:
            return value

    def __repr__(self):
        return '<{mdl}.{cls}()>'.format(
            mdl=self.__class__.__module__, cls=self.__class__.__name__,
        )

    def __setattr__(self, name, value):
        try:
            current = self.__dict__[name]
        except KeyError:
            current = None
        if isinstance(current, _PropertyDescriptor):
            current.setValue(value)
        else:
            super(Action, self).__setattr__(name, value)


# =============================================================================


class _PropertyDescriptor(object):
    def __init__(self, name, value, atype, valid, settable=True):
        self._name = str(name)
        self._value = value
        self._atype = atype
        self._valid = valid
        self._settable = settable

    def getValue(self):
        return self._value

    def setValue(self, value):
        if not self._settable:
            raise AttributeError('Attribute "{0}" is not settable.'.format(self._name))
        if not isinstance(value, self._atype):
            raise TypeError('Given value must be of type {0}.'.format(str(self._atype)))
        if self._valid != None:
            if value in self._valid:
                self._value = value
            else:
                raise ValueError(
                    'Given value is invalid, valid values are: {0}'.format(
                        ', '.join([str(s) for s in self._valid])
                    )
                )
        self._value = value

    def __repr__(self):
        return '<{mdl}.{cls}(name={name},value={val},atype={atype})>'.format(
            mdl=self.__class__.__module__,
            cls=self.__class__.__name__,
            name=repr(self._name),
            val=repr(self._value),
            atype=repr(self._atype),
        )


# =============================================================================
