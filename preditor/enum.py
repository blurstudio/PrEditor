from __future__ import absolute_import

import abc
import re
from builtins import str as text
from numbers import Number

from future.utils import iteritems, with_metaclass
from past.builtins import long

# =============================================================================
# CLASSES
# =============================================================================


class _MetaEnumGroup(type):
    """An EnumGroup metaclass."""

    def __new__(cls, className, bases, classDict):  # noqa: B902
        newCls = type.__new__(cls, className, bases, classDict)
        newCls.__init_enums__()
        newCls._cls = cls
        newCls._clsName = className
        newCls._clsBases = bases
        newCls._clsDict = classDict
        return newCls

    def __call__(cls, number):
        number = int(number)
        e = cls.Nothing
        for enum in cls._ENUMERATORS:
            if enum & number:
                if e:
                    e = e | enum
                else:
                    e = enum
        return e

    def __getitem__(cls, key):
        if isinstance(key, Number):
            return list(cls)[int(key)]
        elif isinstance(key, slice):
            # If a Enum is passed convert it to its labelIndex
            start = key.start
            stop = key.stop
            if isinstance(start, Enum):
                start = start.labelIndex
            if isinstance(stop, Enum):
                stop = stop.labelIndex
            return list(cls)[slice(start, stop, key.step)]
        else:
            return getattr(cls, str(key))

    def __instancecheck__(cls, inst):
        if type(inst) == cls:
            return True
        if isinstance(inst, cls._cls):
            return True
        return False

    def __iter__(cls):
        for e in cls._ENUMERATORS:
            yield e

    def __len__(cls):
        return len(cls._ENUMERATORS)

    def __repr__(cls):
        return '<{mdl}.{cls}({enums})>'.format(
            mdl=cls._clsDict.get('__module__', 'unknown'),
            cls=cls._clsName,
            enums=cls.join(),
        )

    def __str__(cls):
        return '{0}({1})'.format(cls._clsName, cls.join())


# =============================================================================


class Enum(with_metaclass(abc.ABCMeta, object)):
    """A basic enumerator class.

    Enumerators are named values that act as identifiers.  Typically, a
    list of enumerators are component pieces of an `EnumGroup`.

    Example::

        class Suit(Enum):
            pass

        class Suits(EnumGroup):
            Hearts = Suit()
            Spades = Suit()
            Clubs = Suit()
            Diamonds = Suit()

    Enum objects can be combined and compared using binary "and" and "or"
    operations.

    Example::

        mySuits = Suits.Hearts | Suits.Spades

        if Suits.Hearts & mySuits:
            print("This is true!")

        if Suits.Clubs & mySuits:
            print("This is false!")

    Attributes:
        name: The name of the enumerator.
        number: The integer value representation of the enumerator.
        label: The enumerator's label.
        labelIndex: The enumerator's index within its parent EnumGroup.
    """

    _CREATIONORDER = 0

    def __init__(self, number=None, label=None, **kwargs):
        """Initializes a new Enum object.

        In addition to the named arguments listed below, keyword arguments
        may be given that will be set as attributes on the Enum.

        Args:
            number(int): The integer representation of the Enum. The default
                is to have this number determined dynamically based on its
                place with the parent EnumGroup.
            label(str): The Enum's label. The default is to inherit the
                attribute name the Enum is associated with in its parent
                EnumGroup.
        """
        self._creationOrder = Enum._CREATIONORDER
        Enum._CREATIONORDER += 1
        self._name = None
        self._number = number
        self._label = label
        self._labelIndex = None
        self._cmpLabel = None
        self._cmpName = None
        self._enumGroup = None
        if kwargs:
            self.__dict__.update(kwargs)

    @property
    def name(self):
        """The name of the Enum."""
        return self._name

    @property
    def number(self):
        """The number representation of the Enum."""
        return self._number

    @property
    def label(self):
        """The Enum's label."""
        return self._label

    @property
    def labelIndex(self):
        """The Enum's index within its parent EnumGroup."""
        return self._labelIndex

    def _setName(self, name):
        if name is None:
            self._name = None
            self._cmpName = None
        else:
            self._name = name
            self._cmpName = name.strip('_ ')

    def _setLabel(self, label):
        if label is None:
            self._label = None
            self._cmpLabel = None
        else:
            self._label = label
            self._cmpLabel = label.replace(' ', '').replace('_', '')

    def __add__(self, other):
        return self.__or__(other)

    def __and__(self, other):
        if isinstance(other, Enum):
            other = int(other)
        return int(self) & other

    def __call__(self):
        return int(self)

    def __cmp__(self, value):
        if not isinstance(value, Enum):
            return -1
        return self.number - value.number

    def __lt__(self, value):
        return self.__cmp__(value) < 0

    def __eq__(self, value):
        if value is None:
            return False
        if isinstance(value, Enum):
            return self.number == value.number
        if isinstance(value, (int, long)):
            return self.number == value
        if isinstance(value, str) or isinstance(value, text):
            if self._compareStr(value):
                return True
        return False

    def __hash__(self):
        return self.number

    def __index__(self):
        return self.number

    def __int__(self):
        return self.number or 0

    def __invert__(self):
        return ~int(self)

    def __ne__(self, value):
        return not self.__eq__(value)

    def __nonzero__(self):
        return bool(int(self))

    def __or__(self, other):
        o = other
        if isinstance(other, Enum):
            o = int(other)
        # No need to return a CompositeEnum if one of these is Nothing
        if o == 0:
            return self
        v = int(self)
        if v == 0:
            return other
        value = v | o
        label = '{0} {1}'.format(str(self), str(other))
        name = '{0}_{1}'.format(str(self), str(other))

        class CompositeEnum(Enum):
            def __init__(ss, number, lbl, name):  # noqa: N805,B902
                super(CompositeEnum, ss).__init__(number, lbl)
                ss._name = name

        # Register our composite enum class as a virtual
        # subclass of this enum's class, plus the same for
        # the other enum if it's an Enum object.  This
        # will make the composite enum isinstance check true
        # against both.
        type(self).register(CompositeEnum)
        if isinstance(other, Enum):
            type(other).register(CompositeEnum)
        return CompositeEnum(value, label, name)

    def __rand__(self, other):
        if isinstance(other, Enum):
            other = int(other)
        return other & int(self)

    def __repr__(self):
        return '<{mdl}.{cls}.{name}>'.format(
            mdl=self.__class__.__module__,
            cls=self.__class__.__name__,
            name=str(self.name),
        )

    def __ror__(self, other):
        return self | other

    def __rxor__(self, other):
        return self ^ other

    def __str__(self):
        if self.name:
            return self.name
        return self.label or ''

    def __xor__(self, other):
        if isinstance(other, Enum):
            other = int(other)
        return int(self) ^ other

    def _compareStr(self, inStr):
        return inStr.replace(' ', '').replace('_', '') in (
            self._cmpLabel,
            self._cmpName,
        )


# =============================================================================


class EnumGroup(with_metaclass(_MetaEnumGroup, object)):
    """A container class for collecting, organizing, and accessing Enums.

    An EnumGroup class is a container for Enum objects.  It provides
    organizational convenience, and in most cases handles the generation
    and assignment of Enum numbers, names, and labels.

    Example::

        class Suit(Enum):
            pass

        class Suits(EnumGroup):
            Hearts = Suit()
            Spades = Suit()
            Clubs = Suit()
            Diamonds = Suit()

    The above example outlines defining an enumerator, and grouping
    four of them inside of a group.  This provides a number of things,
    including references by attribute, name, and index.  Also provided
    is an "All" attribute, if one is not explicitly assigned, it will be
    a CompositeEnum of all the defined enums, and compare true against
    any members of the group via the binary "and" operator. Also provided
    is an "Nothing" attribute, if one is not explicitly assigned, it
    compares false against any members of the group and when converted to
    a int its value will be zero.

    Example::

        # By attribute.
        Suits.Hearts

        # By name.
        Suits['Hearts']

        suitList = list(Suits)

        if Suits.Hearts & Suits.All:
            print("This is true!")

    You can also pass a int value as a index lookup. If you pass a int value it
    will return the object by its index. This means you can not lookup composite
    Enum objects as 3 returns the third index which in the above example is Diamonds.
    The index value for Enum is stored on its labelIndex property.

    Example::

        print(Suits.Diamonds.labelIndex)

        if Suits.Diamonds == Suits[3]:
            print("This is true!")

    An EnumGroup can be sliced by passing an Enum object or its labelIndex value for
    start and stop, returning a list of matching Enums.

    Example::

        # All Enums between Spades and Diamonds
        Suits[Suits.Spades:Suits.Diamonds]

        # All Enums between Spades and Clubs including Clubs
        Suits[Suits.Spades:Suits.Clubs.labelIndex+1]

    An EnumGroup can also act as a factory for composite Enum objects.
    If a known composite value is available, like 3, which is the
    combination of enum values 1 and 2, a composite Enum object can
    be constructed.

    Example::

        comp = Suits(3)

        if Suits.Hearts & comp:
            print("This is true!")

        if Suits.Clubs & comp:
            print("This is false!")

    If one of the Enum's has the default keyword argument set to True, then that Enum
    is also exposed as the "Default" attribute. Additionally all other Enum's will have
    a default property added and set to False.

    Example::

        class Suits(EnumGroup):
            Hearts = Suit()
            Spades = Suit(default=True)

        assert Suits.Hearts.default == False
        assert Suits.Spades.default == True
        assert Suits.Default == Suits.Spades

    Attributes:
        All: The sum of all members.
        Nothing: None of the members.
    """

    _ENUMERATORS = None
    _copyCount = 1
    All = 0
    Nothing = 0

    def __init__(self):
        raise InstantiationError('Unable to instantiate static class EnumGroup.')

    @classmethod
    def append(cls, *args, **kwargs):
        """Appends additional enumerators to the EnumGroup.

        New members can be provided as ordered arguments where the
        each Enum's label is used to determine the attribute name, or
        by keyword arguments where the key is the attribute name and
        the Enum is the value.  When using an Enum's label to determine
        its name, any spaces in the label will be converted to underscores.

        Example:
            Suits.append(Suit(None, 'Funky'), Foo=Suit())

            # The "Funky" and "Foo" suits are now available.
            Suits.Funky
            Suits.Foo

        Raises:
            ValueError
        """
        if [e for e in (list(args) + list(kwargs.values())) if not isinstance(e, Enum)]:
            raise ValueError('Given items must be of class Enum.')
        if [e for e in args if not e.label]:
            raise ValueError('Enums given as ordered arguments must have a label.')
        for e in args:
            setattr(cls, cls._labelToVarName(e.label), e)
        for n, e in iteritems(kwargs):
            setattr(cls, n, e)
        # reset All and Nothing -- this is necessary so that All is regenerated
        # and so that Nothing is not included when finding the member Enums.
        cls.All = 0
        cls.Nothing = 0
        cls.__init_enums__()

    @classmethod
    def copy(cls, name=None):
        """Returns a new class type from this class without any Enums assigned.

        If name is not provided it will automatically generate a new class name.
        For example if the EnumGroup class named DefaultEnums has been copied
        twice the new class name will be "DefaultEnums_3".
        If you provide name it will not check for duplicates.

        Args:
            name (str|None): The name to give the new class. Defaults to None

        Returns:
            EnumGroup: A new Class type.
        """
        if not name:
            # Generate a unique name for the class if one was not provided
            name = '{name}_{count}'.format(name=cls.__name__, count=cls._copyCount)
            cls._copyCount += 1
        return type(name, cls.__bases__, dict(cls.__dict__))

    @classmethod
    def fromLabel(cls, label, default=None):
        """Gets an enumerator based on the given label.

        If a default is provided and is not None, that value will be returned
        in the event that the given label does not exist in the EnumGroup.  If
        no default is provided, a ValueError is raised.

        Args:
            label(str): The label to look up.
            default(*): The default value to return if the label is not found.

        Raises:
            ValueError: Raised if default is None and the given label does not
                exist in the EnumGroup.

        Returns:
            Enum
        """
        label = str(label)
        for e in cls._ENUMERATORS:
            if e.label == label:
                return e
        if default is not None:
            return default
        raise ValueError('No enumerators exist with the given label.')

    @classmethod
    def fromValue(cls, value, default=None, allowComposite=False):
        """Gets an enumerator based on the given value.

        If a default is provided and is not None, that value will be returned
        in the event that the given label does not exist in the EnumGroup.  If
        no default is provided, a ValueError is raised.

        Args:
            value (int): The value to look up.
            default (*): The default value to return if the label is not found.
            allowComposite (bool, optional): If True a composite enums will be
                created when provided a value that is the sum of multiple enum
                values.  Otherwise, a ValueError will be raised.  Defaults to
                False.

        Returns:
            Enum

        Raises:
            ValueError: Raised if default is None and the given label does not
                exist in the EnumGroup.
        """
        value = int(value)
        composite = None
        for e in cls._ENUMERATORS:
            eVal = int(e)
            if eVal == value:
                return e
            if allowComposite and eVal & value:
                composite = e if composite is None else (composite | e)
        if composite is not None and int(composite) == value:
            return composite
        if default is not None:
            return default
        raise ValueError('No enumerators exist with the given value.')

    @classmethod
    def join(cls, include=None, separator=','):
        """Joins all child Enums together into a single string.

        The string representation of each Enum is joined using the
        given separator.

        Args:
            include(int|Enum): Only enumerators that compare via bitwise "and" against
                the given int or Enum will be returned.  Default is EnumGroup.All.
            separator(str): The separator to use.  Default is ",".

        Returns:
            str: The joined enumerators.
        """
        include = include is None and cls.All or include
        return str(separator).join(
            [str(e) for e in cls._ENUMERATORS if e & int(include)]
        )

    @classmethod
    def labels(cls):
        """A generator containing all Enum labels in the EnumGroup."""
        return (e.label for e in cls._ENUMERATORS)

    @classmethod
    def names(cls):
        """A generator containing all Enum names in the EnumGroup."""
        return (e.name for e in cls._ENUMERATORS)

    @classmethod
    def split(cls, string, separator=','):
        """Splits the given string and returns the corresponding Enums.

        The string is split using the provided separator, and all names
        contained within must be attributes of the EnumGroup class that
        is performing the split.

        Args:
            string(str): The string containing the desired Enum names.
            separator(str): The separator to split on.  Default is ','.

        Raises:
            AttributeError

        Returns:
            list(Enum, ...): The list of resulting Enum objects.
        """
        names = str(string).split(str(separator))
        return [getattr(cls, n) for n in names]

    @classmethod
    def values(cls):
        """A generator containing all Enum values in the EnumGroup."""
        return (int(e) for e in cls._ENUMERATORS)

    @classmethod
    def __init_enums__(cls):
        enums = []
        default_enum = None

        orderedEnums = sorted(
            [
                (k, v)
                for k, v in iteritems(cls.__dict__)
                if isinstance(v, Enum) and k not in ('All', 'Nothing')
            ],
            key=lambda i: i[1]._creationOrder,
        )
        for name, value in orderedEnums:
            enums.append(value)
            value._enumGroup = cls
            value._setName(name)
            if value.label is None:
                value._setLabel(cls._varNameToLabel(name))
            # Check for a default property and raise a error if more than one is found
            if hasattr(value, 'default') and value.default:
                if default_enum is not None:
                    raise ValueError(
                        (
                            '"{}" already defines default and "{}" is trying to '
                            'claim the default'
                        ).format(default_enum, value)
                    )
                default_enum = value

        enumNumbers = [enum.number for enum in enums if enum.number]
        num = 1
        for enum in enums:
            if enum._number is None:
                while num in enumNumbers:
                    num *= 2
                enum._number = num
                enumNumbers.append(num)
        enums.sort()
        labelIndex = 0
        for enum in enums:
            if enum._label is not None:
                enum._labelIndex = labelIndex
                labelIndex += 1
            # Add a default property to all enums for consistency
            if default_enum and not hasattr(enum, 'default'):
                enum.default = False
        cls._ENUMERATORS = enums
        # Build the All object if its not defined
        if isinstance(cls.All, int):
            for e in enums:
                if isinstance(cls.All, int):
                    cls.All = e
                else:
                    cls.All |= e
        # Build the Nothing object if its not defined
        if isinstance(cls.Nothing, int) and enums:
            processed = set()
            for i, enum in enumerate(enums):
                enumClass = enum.__class__
                if i == 0:
                    # Create the Nothing instance from the first class type
                    cls.Nothing = enumClass(0, 'Nothing')
                elif enumClass not in processed:
                    # Register our Nothing enum's class as a virtual
                    # subclass of any additional enum classes. This
                    # will make the Nothing enum isinstance check true
                    # against all Enums in this EnumGroup.
                    enumClass.register(cls.Nothing.__class__)
                processed.add(enumClass)
        # If a default was specified, store it on the Default argument
        if default_enum and not hasattr(cls, 'Default'):
            cls.Default = default_enum
            # Ensure the All and Nothing Enum's have a default as well
            cls.All.default = False
            if enums:
                cls.Nothing.default = False

    @classmethod
    def _varNameToLabel(cls, varName):
        label = str(varName)
        label = ' '.join(re.findall('[A-Z]+[^A-Z]*', label))
        label = re.sub(r'[_\s]+', ' ', label)
        return label

    @classmethod
    def _labelToVarName(cls, label):
        name = str(label)
        name = re.sub(r'\s+', '_', name)
        return name


# =============================================================================
class Incrementer(object):
    """A class that behaves similarly to c i++ or ++i.

    Once you init this class, every time you call it it will update count and return the
    previous value like c's i++. If you pass True to pre, it will increment then return
    the new value like c's ++i.

    Args:
        start (int): Start the counter at this value. Defaults to Zero.

        increment (int): increment by this value. In most cases it should be 1 or -1.
            Defaults to one.

        pre (bool): If true calling the object will return the incremented value. If
            False it will return the current value and increment for the next call.
            Defaults to False.

    Attributes:
        count: The current value.
        increment: The incremnt added to count
        pre: Should it preform a ++i or i++ operation when called.
    """

    def __init__(self, start=0, increment=1, pre=False):
        super(Incrementer, self).__init__()
        self.count = start
        self.increment = increment
        self.pre = pre

    def __call__(self):
        if self.pre:
            self.count += self.increment
            return self.count
        ret = self.count
        self.count += self.increment
        return ret

    def __repr__(self):
        return '{}.{}(start={}, increment={}, pre={!r})'.format(
            self.__module__, type(self).__name__, self.count, self.increment, self.pre
        )

    def __str__(self):
        return str(self.count)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class InstantiationError(Exception):
    pass


# =============================================================================
