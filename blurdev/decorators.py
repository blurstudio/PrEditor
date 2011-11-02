##
# 	\namespace	python.blurdev.decorators
#
# 	\remarks	Defines some deocrators that are commonly useful
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		03/23/11
#

from blurdev import debug


class abstractmethod(object):
    def __init__(self, method):
        self._basemethod = method

    def __call__(self, *args, **kwds):
        """
            \remarks	attempts to call the abstract method for this instance with the inputed arguments and variables
                        if the debugging mode is set to a high level, then this will throw an implementation error, otherwise
                        it will return the result of the method
            \param		*args		arguments
            \param		**kwds		keywords
            \return		<variant>
        """
        # when debugging, raise an error
        if debug.isDebugLevel(debug.DebugLevel.High):
            raise NotImplementedError
        else:
            debug.debugObject(
                self._basemethod,
                'Abstract implementation is not implemented',
                debug.DebugLevel.Mid,
            )

        return self._basemethod(self._basemethod, *args, **kwds)

    def basemethod(self):
        return self._basemethod


def pendingdeprecation(function):
    def newFunction(*args, **kwargs):
        if debug.isDebugLevel(debug.DebugLevel.High):
            raise PendingDeprecationWarning(
                debug.debugObjectString(
                    function, 'This method will be removed in the future.'
                )
            )
        else:
            debug.debugObject(
                function,
                'This method will be removed in the future',
                debug.DebugLevel.Low,
            )
        return function(*args, **kwargs)

    newFunction.__name__ = function.__name__
    newFunction.__doc__ = function.__doc__
    newFunction.__dict__ = function.__dict__
    return newFunction
