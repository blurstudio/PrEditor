import sys

from .constants import *

# =============================================================================
# CLASSES
# =============================================================================


class _ArgNoDefault(object):
    pass


# =============================================================================


class _Argument(object):
    def __init__(self, name, atype, default, propertyName, validValues, settable=True):
        self._name = name
        self._default = default
        self._found = False
        self._value = None
        self._atype = atype
        self._propertyName = propertyName
        self._validValues = validValues
        self._settable = settable

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        if isinstance(self._default, _ArgNoDefault):
            msg = 'Required argument {name} not provided.'.format(name=self.name)
            raise ArgumentHasNoDefaultError(msg)
        else:
            return self._default

    @property
    def found(self):
        return self._found

    @found.setter
    def found(self, state):
        self._found = state

    @property
    def propertyName(self):
        return self._propertyName

    @property
    def settable(self):
        return self._settable

    @property
    def atype(self):
        return self._atype

    @property
    def validValues(self):
        return self._validValues

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if isinstance(value, self.atype):
            if self.validValues:
                if value in self.validValues:
                    self._value = value
                else:
                    msg = 'Valid arguments for {name} are: {valid}'.format(
                        name=self.name,
                        valid=', '.join([str(v) for v in self.validValues]),
                    )
                    raise ValueError(msg)
            else:
                self._value = value
        else:
            msg = 'Given value for argument {name} is not the correct type.'.format(
                name=self.name,
            )
            raise ArgumentTypeIncorrectError(msg)

    def __del__(self):
        self.found = False

    def __repr__(self):
        return '<{mdl}.{cls}(name={name},value={val},atype={atype})>'.format(
            mdl=self.__class__.__module__,
            cls=self.__class__.__name__,
            name=repr(self._name),
            val=repr(self._value),
            atype=repr(self._atype),
        )


# =============================================================================


class _ChildActionContainer(object):
    def __init__(self, childClass, name, argRename=dict()):
        self._childClass = childClass
        self._name = name
        self._argRename = argRename

    @property
    def argRename(self):
        return self._argRename

    @property
    def childClass(self):
        return self._childClass

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return '<{mdl}.{cls}(childClass={cc},name={name})>'.format(
            mdl=self.__class__.__module__,
            cls=self.__class__.__name__,
            cc=repr(self.childClass),
            name=repr(self._name),
        )


# =============================================================================


class __BaseApplicationDecorator(object):
    """The base class for application-abstractable decorators.
    """

    def __init__(self, app=Apps.All):
        """Initializes the application-abstraction portion of the decorator.

        Args:
            app(`App`): The enum representation of the application context that
                the decorated function or method supports.

        Returns:
            N/A

        Raises:
            N/A
        """
        if not isinstance(app, App):
            raise TypeError('Given application enum must be of type App.')
        self._app = app


# =============================================================================


class argproperty(object):
    """Decorator class that is used to add an argument to an `Action`.
    """

    __order = 0

    def __init__(
        self, atype, name=None, default=_ArgNoDefault(), valid=None, settable=True
    ):
        """Initializes the argproperty decorator.

        Args:
            atype(type/tuple): A type or tuple of typed accepted by the argument.
            name(str): The keyword argument name, if different from the name of the
                decorated method's name.
            default(*): The default value for the argument.  This also indicates that
                the argument being defined is optional.  Not specifying a default for
                the argument will imply that it is a required argument.
            valid(list): A list of values accepted by the argument.
            settable(bool): Whether the argument is settable.  Default is False.

        Returns:
            N/A

        Raises:
            N/A
        """
        self._name = name
        self._atype = atype
        self._default = default
        self._validValues = valid
        self._settable = settable

    def __call__(self, function):
        def newFunction(*args):
            return getattr(args[0], '_{property}'.format(property=function.__name__))

        if self._name:
            name = self._name
        else:
            name = str(function.func_name)
        newFunction.__actionArgument = _Argument(
            name,
            self._atype,
            self._default,
            function.__name__,
            self._validValues,
            self._settable,
        )
        newFunction.__order = self.__class__.__order
        self.__class__.__order += 1
        return newFunction


# =============================================================================


class applicationmethod(__BaseApplicationDecorator):
    """Decorator class that is used to add an application-specific method to
    an `Action`.

    Args:
        app(`App`): An enum specification of the application context for the method.
        name(str): The name to use for the application-abstract attribute that this
            method will be attached to when in the correct application context.

    Returns:
        N/A

    Raises:
        N/A
    """

    def __init__(self, app, name):
        super(applicationmethod, self).__init__(app=app)
        self._name = str(name)

    def __call__(self, function):
        function.__appMethodName = self._name
        function.__appMethodApp = self._app
        return function


# =============================================================================


class applicationimporter(__BaseApplicationDecorator):
    """Decorator that tags a method as being an application-specific module
    importer.
    """

    def __call__(self, function):
        def persistentLocals(func, *args, **kwargs):
            def tracer(frame, event, arg):
                if event == 'return':
                    func._locals = frame.f_locals.copy()

            # Tracer is activated on next call, return or exception.
            sys.setprofile(tracer)
            try:
                # Trace the function call.
                res = func(*args, **kwargs)
            finally:
                # Disable the tracer and replace with old one.
                sys.setprofile(None)
            return res

        def newFunction(*args):
            ret = persistentLocals(function, *args)
            newFunction._locals = function._locals

        newFunction.__supportedApp = self._app
        newFunction.__actionAppImporter = True
        return newFunction


# =============================================================================


class childaction(object):
    """Decorator class that is used to add a child to an `Action`.
    """

    __order = 0

    def __init__(self, cls, argRename=dict()):
        """Initializes the childaction decorator.

        Args:
            cls(cls): The class of the child action.
            argRename(dict): A dict containing key-value pairs for redirecting
                a given keyword argument to a different keyword argument in the
                parent `Action`.

        Returns:
            N/A

        Raises:
            N/A
        """
        self._cls = cls
        self._argRename = argRename

    def __call__(self, function):
        def newFunction(*args):
            return getattr(args[0], function.__name__)

        newFunction.__container = _ChildActionContainer(
            self._cls, function.__name__, self._argRename,
        )
        newFunction.__order = self.__class__.__order
        self.__class__.__order += 1
        return newFunction


# =============================================================================


class enterhook(__BaseApplicationDecorator):
    """Decorator that tags a method as being the action's enter hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionEnterHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class exithook(__BaseApplicationDecorator):
    """Decorator that tags a method as being the action's exit hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionExitHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class executehook(__BaseApplicationDecorator):
    """Decorator that tags a method as being the action's execute hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionExecuteHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class prechildhook(__BaseApplicationDecorator):
    """Decorator that tags a method as being a pre-child hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionPreChildHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class postchildhook(__BaseApplicationDecorator):
    """Decorator that tags a method as being a post-child hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionPostChildHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class preexecutehook(__BaseApplicationDecorator):
    """Decorator that tags a method as being a pre-execute hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionPreExecuteHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================


class postexecutehook(__BaseApplicationDecorator):
    """Decorator that tags a method as being a post-execute hook.
    """

    __order = 0

    def __call__(self, function):
        function.__actionPostExecuteHook = True
        function.__supportedApp = self._app
        function.__order = self.__class__.__order
        self.__class__.__order += 1
        return function


# =============================================================================
