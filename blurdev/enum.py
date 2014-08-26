""" Python based enumartion class, create and parse binary classes

    The enum module defines a single class -- :class:`enum` -- to act as an 
    enumerated type similar to the enumerated type present in other languages.
    
    A short example::
    
        >>> Colors = enum("Red", "Yellow", "Blue")
        >>> Color.Red
        1
        >>> Color.Yellow
        2
        >>> Color.Blue
        4
        >>> Color.labelByValue(Color.Blue)
        'Blue'
    
"""

import re
import sys


class enum(object):
    INDICES = xrange(sys.maxint)  # indices constant to use for looping

    def __call__(self, key):
        return self.value(key)

    def __getattr__(self, key):
        if key == '__name__':
            return 'enum'
        else:
            raise AttributeError, key

    def __init__(self, *args, **kwds):
        """ Takes the provided arguments adds them as properties of this object. For each argument you
        pass in it will assign binary values starting with the first argument, 1, 2, 4, 8, 16, ....
        If you pass in any keyword arguments it will store the value.
        
        Note: Labels automaticly add spaces for every capital letter after the first, so do not use
        spaces for args, or the keys of kwargs or you will not be able to access those parameters.
        
        :param *args: Properties with binary values are created
        :param **kwds: Properties with passed in values are created
        
        Example::
            >>> e = blurdev.enum.enum('Red', 'Green', 'Blue', White=7)
            >>> e.Blue
            4
            >>> e.White
            7
            >>> e.Red | e.Green | e.Blue
            7
        """
        super(enum, self).__init__()
        self._keys = list(args) + kwds.keys()
        self._compound = kwds.keys()
        self._descr = {}
        key = 1
        for i in range(len(args)):
            self.__dict__[args[i]] = key
            key *= 2

        for kwd, value in kwds.items():
            self.__dict__[kwd] = value

        if not ('All' in args or 'All' in kwds):
            out = 0
            for k in self._keys:
                out |= self.__dict__[k]
            self.__dict__['All'] = out

    def count(self):
        return len(self._keys)

    def description(self, value):
        """ Returns the description string for the provided value
        :param value: The binary value of the description you want
        """
        return self._descr.get(value, '')

    def matches(self, a, b):
        """ Does a binary and on a and b
        :param a: First item
        :param b: Second item
        :returns: boolean
        """
        return a & b != 0

    def hasKey(self, key):
        return key in self._keys

    def labels(self, byVal=False):
        """ Returns a list of all provided parameters.
        :param byVal: Sorts the labels by their values. Defaults to False
        :returns: A list of labels as strings
        """
        if byVal:
            return [
                ' '.join(re.findall('[A-Z]+[^A-Z]*', key))
                for key in sorted(self.keys(), key=lambda i: getattr(self, i))
            ]
        return [' '.join(re.findall('[A-Z]+[^A-Z]*', key)) for key in self.keys()]

    def labelByValue(self, value):
        """ Returns the label for a specific value. Labels automaticly add spaces
        for every capital letter after the first.
        :param value: The value you want the label for
        """
        return ' '.join(re.findall('[A-Z]+[^A-Z]*', self.keyByValue(value)))

    def isValid(self, value):
        """ Returns True if this value is stored in the parameters.
        :param value: The value to check
        :return: boolean. Is the value stored in a parameter.
        """
        return self.keyByValue(value) != ''

    def keyByIndex(self, index):
        """ Finds the key based on a index. This index contains the *args in the order they were passed in
        then any **kwargs's keys in the order **kwargs.keys() returned. This index is created when the class
        is initialized.
        :param index: The index to lookup
        :returns: The key for the provided index or a empty string if it was not found.
        """
        if index in range(self.count()):
            return self._keys[index]
        return ''

    def keyByValue(self, value):
        """ Return the parameter name for a specific value. If not found returns a empty string.
        :param value: The value to find the parameter name of.
        :returns: String. The parameter name or empty string.
        """
        for key in self._keys:
            if self.__dict__[key] == value:
                return key
        return ''

    def keys(self):
        """ Returns a list of parameter names
        """
        return self._keys

    def value(self, key, caseSensitive=True):
        """ Return the value for a parameter name
        :param key: The key to get the value for
        :param caseSensitive: Defaults to True
        :returns: The value for the key, or zero if it was not found
        """
        if caseSensitive:
            return self.__dict__.get(str(key), 0)
        else:
            key = str(key).lower()
            for k in self.__dict__.keys():
                if k.lower() == key:
                    return self.__dict__[k]
            return 0

    def values(self):
        """ Returns a list of all values for stored parameters
        """
        return [self.__dict__[key] for key in self.keys()]

    def valueByLabel(self, label, caseSensitive=True):
        """
        Return the binary value fromt the given label.
        :param label: The label you want the binary value of
        :param caseSensitive: Defaults to True
        :returns: the bindary value of the label as a int
        """
        return self.value(''.join(str(label).split(' ')), caseSensitive=caseSensitive)

    def valueByIndex(self, index):
        """ Returns the stored value for the index of a parameter.
        .. seealso:: :meth:`keyByValue`
        .. seealso:: :meth:`value`
        """
        return self.value(self.keyByIndex(index))

    def index(self, key):
        """ Return the index for a key.
        :param key: The key to find the index for
        :returns: Int, The index for the key or -1
        .. seealso:: :meth:`keyByValue`
        """
        if key in self._keys:
            return self._keys.index(key)
        return -1

    def indexByValue(self, value):
        """ Return the index for a value.
        :param value: The value to find the index for
        :returns: Int, the index of the value or -1
        .. seealso:: :meth:`keyByValue`
        """
        for index in range(len(self._keys)):
            if self.__dict__[self._keys[index]] == value:
                return index
        return -1

    def toString(self, value, default='None', sep=' '):
        """ For the provided value return the parameter name(s) seperated by sep. If you provide
        a int that represents two or more binary values, it will return all parameter names that
        binary value represents seperated by sep. If no meaningful value is found it will return
        the provided default.
        :param value: The value to return parameter names of
        :param default: If no parameter were found this is returned. Defaults to 'None'
        :param sep: The parameters are joined by this value. Defaults to a space.
        :return: Returns a string of values or the provided default
        .. seealso:: :meth:`fromString`
        """
        parts = []
        for key in self._keys:
            if not key in self._compound and value & self.value(key):
                parts.append(key)
        if parts:
            return sep.join(parts)
        return default

    def fromString(self, labels, sep=' '):
        """ Returns the value for a given string. This function binary or's the parameters, so it 
        may not work well when using **kwargs
        :param labels: A string of parameter names.
        :param sep: The seperator used to seperate the provided parameters.
        :returns: The found value
        .. seealso:: :meth:`value`
        .. seealso:: :meth:`toString`
        """
        parts = str(labels).split(sep)
        value = 0
        for part in parts:
            value |= self.value(part)
        return value

    def setDescription(self, value, descr):
        """ Used to set a description string for a value.
        :param value: The parameter value to set the description on
        :param descr: The description string to set on a parameter
        """
        self._descr[value] = descr

    matches = classmethod(matches)
