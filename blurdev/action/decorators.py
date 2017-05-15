# pylint: disable=protected-access, invalid-name, too-few-public-methods, line-too-long
import sys

from .constants import Apps, App
from .exceptions import ArgumentHasNoDefaultError, ArgumentTypeIncorrectError

# =============================================================================
# CLASSES
# =============================================================================


class _ArgNoDefault(object):
    pass


# =============================================================================


class _Argument(object):
    def __init__(
        self,
        name,
        atype,
        default,
        propertyName,
        validValues,
        settable=True,
        allowNone=False,
        defaultInstance=False,
        **kwargs
    ):
        self._name = name
        self._defaultInstance = defaultInstance
        self._default = default
        self._found = False
        self._value = None
        self._atype = atype
        self._propertyName = propertyName
        self._validValues = validValues
        self._settable = settable
        self._allowNone = allowNone
        self._kwargs = kwargs
        self._parent = None

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        if self._defaultInstance:
            atype = self._atype[0] if isinstance(self._atype, tuple) else self._atype
            if isinstance(atype, type):
                return atype()
            else:
                msg = 'Invalid leading argument type for {cls}.{name}: {tpe}'.format(
                    cls=type(self.parent).__name__, name=self.name, tpe=atype,
                )
                raise TypeError(msg)
        elif isinstance(self._default, _ArgNoDefault):
            msg = 'Required argument {cls}.{name} not provided'.format(
                cls=type(self.parent).__name__, name=self.name,
            )
            raise ArgumentHasNoDefaultError(msg)
        else:
            return self._default

    @property
    def required(self):
        if self._defaultInstance:
            return False
        return isinstance(self._default, _ArgNoDefault)

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

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def allowNone(self):
        return self._allowNone

    @value.setter
    def value(self, value):
        if isinstance(value, self.atype):
            if self.validValues:
                if value in self.validValues:
                    self._value = value
                else:
                    msg = 'Valid arguments for {cls}.{name} are: {valid}'.format(
                        cls=type(self.parent).__name__,
                        name=self.name,
                        valid=', '.join([str(v) for v in self.validValues]),
                    )
                    raise ValueError(msg)
            else:
                self._value = value
        elif self._allowNone and value is None:
            self._value = value
        else:
            msg = (
                'Given value for argument {cls}.{name} is not the correct type.\n'
                'Expected: {exp}\nGot: {got}\nWith Value: {value}'.format(
                    cls=type(self.parent).__name__,
                    name=self.name,
                    got=type(value),
                    exp=self.atype,
                    value=value,
                )
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
    def __init__(self, childClass, name, order, argRename=None, **kwargs):
        self._childaction__order = order
        self._childClass = childClass
        self._name = name
        self._kwargs = kwargs
        if argRename is None:
            self._argRename = {}
        else:
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

    @property
    def kwargs(self):
        return self._kwargs

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
        self,
        atype,
        name=None,
        allowNone=False,
        default=_ArgNoDefault(),
        valid=None,
        settable=True,
        defaultInstance=False,
        **kwargs
    ):
        """Initializes the argproperty decorator.

        Args:
            atype(type/tuple): A type or tuple of types accepted by the argument.
            name(str): The keyword argument name, if different from the name of the
                decorated method's name.
            default(*): The default value for the argument.  This also indicates that
                the argument being defined is optional.  Not specifying a default for
                the argument and having defaultInstance==False will imply that it is a required argument.
            allowNone(bool): Whether to allow None as the value for this argument. Default to False
            valid(list): A list of values accepted by the argument.
            settable(bool): Whether the argument is settable.  Default is False.
            defaultInstance(bool): If True, the default value is built directly from atype upon
                argument instantiation. This option will override the default value and also
                indicates that the argument being defined is optional. Not specifying a default for
                the argument and having defaultInstance==False will imply that it is a required argument.

        Returns:
            N/A

        Raises:
            N/A
        """
        self._name = name
        self._atype = tuple(atype) if isinstance(atype, (list, tuple)) else (atype,)
        self._default = default
        self._defaultInstance = defaultInstance
        self._validValues = valid
        self._settable = settable
        self._order = self.__class__.__order
        self._allowNone = allowNone
        self._kwargs = kwargs
        self.__class__.__order += 1

    def __call__(self, function, nameOverride=None):
        _nameOverride = nameOverride or function.__name__

        def newFunction(*args):
            return getattr(args[0], '_{property}'.format(property=nameOverride))

        name = self._name if self._name else _nameOverride
        newFunction.__name__ = name

        filteredAtypes = tuple(i for i in self._atype if i is not None)
        allowNone = self._allowNone or (None in self._atype) or self._default is None

        actionArg = _Argument(
            name,
            filteredAtypes,
            self._default,
            _nameOverride,
            self._validValues,
            self._settable,
            allowNone,
            self._defaultInstance,
            **self._kwargs
        )

        # actionArg._argproperty__order = self._order
        newFunction._argproperty__actionArgument = actionArg
        newFunction._argproperty__order = self._order
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

    def __init__(self, cls, argRename=None, **kwargs):
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
        if argRename is None:
            self._argRename = {}
        else:
            self._argRename = argRename
        self._order = self.__class__.__order
        self._kwargs = kwargs
        self.__class__.__order += 1

    def __call__(self, function, nameOverride=None):
        _nameOverride = nameOverride or function.__name__

        def newFunction(*args):
            return getattr(args[0], _nameOverride)

        newFunction.__name__ = _nameOverride
        container = _ChildActionContainer(
            self._cls, _nameOverride, self._order, self._argRename, **self._kwargs
        )
        newFunction._childaction__container = container
        newFunction._childaction__order = self._order
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
