"""
##########################################################
blurdev.action - A framework for building reusable actions.
##########################################################

The action framework is designed to act as the foundation for building reusable
and combinable actions.  These actions act as callables with additional benefits
attached such as child actions, pre- and post-hooks, and argument registration,
parsing, validation, and defaulting.

***************
Getting Started
***************

Actions are an approximation of a command design pattern intended to impose
reusability as well as provide convenience for the programmer.  The nature of
Action class is such that any concrete implementation of an Action can be used
in concert with any other concrete Action.  The attempt is to provide that
structure without imposing artificial limitations on what an Action can do.
Rather, there is an emphasis on HOW an Action does certain things, which
provides the enforced consistency necessary to ensure reusability.  As such,
WHAT an Action does is of little concern to the framework as long as how it
performs its task(s) adheres to the enforced practices.

*****************
Writing an Action
*****************

Writing an action can be broken down into three segments:

* Defining arguments
* Specifying hooks
* Defining children

Defining arguments is handled by the `argproperty` decorator.

::

    argproperty(atype=bool, default=True, settable=True)
    def makeItWork(self):
        pass

In the example above, a "makeItWork" argument has been defined.  This argument
accepts a boolean argument, which defaults to True, and is settable after
instantiation.  The name of the keyword argument is defaulted to the name of
the method that `argproperty` is decorating, though it is possible to map a
keyword argument to a resultant property that does not match its name, as
described in the documentation for `argproperty`.

Various hooks are made available by the Action framework:

* `executehook` runs when the action is called and defined what the action does.
* `preexecutehook` runs before anything else when an action is called.
* `postexecutehook` runs after everything else when an action is called.
* `prechildhook` runs before each child action is executed.
* `postchildhook` runs after each child action is executed.

Of those provided, only `executehook` is required. All may be used multiple
times EXCEPT `executehook`.  If hooks are used multiple times, each hook will
be executed in sequence in the order they are defined within the action.

::

    @preexecutehook()
    def _doSomethingFirst(self):
        print('This is happening first.')

    @executehook()
    def _doSomething(self):
        print('This action is executing.')

    @postexecutehook()
    def _doSomethingLast(self):
        print('This is happening last.')

In the above example, a very simple set of hooks have been setup and will
execute in the order made obvious by the print functions that they contain.

Child actions allow for attaching other actions to run when the parent action
is executed.  This parent-child relationship allows for a hierarchy of execution
of multiple actions as a single, compound event.

::

    @childaction(OtherAction)
    def otherAction(self):
        pass

In the example above, a child action has been defined and stored to a property
called "otherAction" and is of the "OtherAction" class.  When the parent action
is instantiated, the child action will also be instantiated and stored in the
associated property.

Also an option is to add child actions dynamically after instantiation.

::

    myAction = MyAction()
    myAction.addChildActions([OtherAction()])

In the above example, a child action "OtherAction" has been added to the list
of child actions that "MyAction" might already possess.

Another powerful feature is the ability to attach pre- and post-child hooks
to an action, as discussed previously.

::

    @prechildaction()
    def _doSomethingPreChild(self, child):
        print('This is running before {}'.format(str(child)))

    @postchildaction()
    def _doSomethingPostChild(self, child):
        print ('This is running after {}'.format(str(child)))

This allows for checking the state of a child action to potentially perform
additional operations before continuing with the execution phase of the parent
action.  Similarly, the state of the child action can be altered prior to its
execution based on the state of the parent action at the time of execution.

******************
Order of Execution
******************

Default:

* Pre-execute hooks
* Execute hook
* Pre-child hooks
* Child action
* Post-child hooks
* Post-execute hooks

With childrenFirst=True:

* Pre-execute hooks
* Pre-child hooks
* Child action
* Post-child hooks
* Execute hook
* Post-execute hook

***************************
Actions as Context Managers
***************************

Actions can also be defined with context-manager behavior using the following two
decorators:

* enterhook
* exithook

Example:

::

    @enterhook()
    def myEnterFunction(self):
        print("This is happening on enter!")
    
    @exithook()
    def myExitFunction(self, *args, **kwargs):
        print("This is happening on exit!")

This, in turn, allows for using the action with a "with" statement:

::

    with MyAction() as ma:
        print("This is happening in between my enter and exit hooks!")

For more information on context managers and the "with" statement:

`https://docs.python.org/2/reference/compound_stmts.html#with`

***********************
Application Abstraction
***********************

Actions also provide a bevy of methods that allow for implementation for
multiple application contexts within the single action.

The following decorators support application-specific implementations:

* executehook
* preexecutehook
* postexecutehook
* prechildhook
* postchildhook
* enterhook
* exithook

Example:

::

    @executehook(app=Apps.Maya)
    def myExecuteFunctionMaya(self):
        print("This is only happening if we are in Maya!")
    
    @executehook(app=Apps.Max)
    def myExecuteFunctionMax(self):
        print("This is only happening if we are in Max!")

There is also an additional decorator for defining abstracted methods:

* applicationmethod

Example:

::

    @applicationmethod(app=Apps.Maya, name='myMethod')
    def myMethodMaya(self):
        print("This is only happening in Maya!")
    
    @applicationmethod(app=Apps.Max, name='myMethod')
    def myMethodMax(self):
        print("This is only happening in Max!")

In the above example, three attributes will exist on the action once it is
instantiated:

* myMethodMaya
* myMethodMax
* myMethod

The first two are the methods explicitly defined.  The third, myMethod, is the
"abstracted" method, which will point to either "myMethodMaya" or "myMethodMax"
depending on the application context at the time that the action is instantiated.

In this way, there are two different options for defining an abstracted action:

::

    @executehook(app=Apps.Maya)
    def myExecuteFunctionMaya(self):
        print("This is only happening if we are in Maya!")
    
    @executehook(app=Apps.Max)
    def myExecuteFunctionMax(self):
        print("This is only happening if we are in Max!")

Or, alternatively:

::

    @applicationmethod(app=Apps.Maya, name='myMethod')
    def myMethodMaya(self):
        print("This is only happening in Maya!")
    
    @applicationmethod(app=Apps.Max, name='myMethod')
    def myMethodMax(self):
        print("This is only happening in Max!")
    
    @executehook():
    def myExecuteFunction(self):
        self.myMethod()

In both of the above examples, we have an execute hook that is running code
that is context sensitive depending on application context.  Both are acceptable
ways of getting the same result.

Application aware module importers can also be defined, which will run based on
application context, and then promote any local module or class imports to be
globals of your action instance.

* applicationimporter

::

    @applicationimporter(app=Apps.Max)
    def maxImporter(self):
        import Py3dsMax
        import alembic

In the above example, if the action is instantiated from within 3ds Max, the
above importer will be executed, and both the Py3dsMax and alembic module
references will be available from within the action's various methods.

"""

import copy_reg
import types

from .base import *
from .decorators import *
from .constants import *
from .exceptions import *

# =============================================================================
# FUNCTIONS
# =============================================================================

# This allows instancemethod type objects to be pickled.  Since actions
# rely on some tricky stuff that involves storing local copies of
# instancemethods, we will go ahead and register the correct handler.
def _pickle_method(m):
    if not hasattr(m, '__self__'):
        return getattr, (m.__class__, m.__name__)
    else:
        return getattr, (m.__self__, m.__func__.__name__)


copy_reg.pickle(types.MethodType, _pickle_method)

# =============================================================================
