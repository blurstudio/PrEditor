from Qt.QtCore import QObject

from preditor.utils.cute import QtPropertyInit


def test_mutable():
    class PropertyInit(QObject):
        # It is preferred that you pass the class type for default if possible
        a_list = QtPropertyInit("_a_list", list)
        a_dict = QtPropertyInit("_a_dict", dict)
        a_set = QtPropertyInit("_a_set", set)
        # Test passing a mutable object as the default. In most cases doing this
        # should be avoided as it leads to unexpected behavior.
        shared_list = QtPropertyInit("_shared_list", [])
        shared_dict = QtPropertyInit("_shared_dict", {})
        shared_set = QtPropertyInit("_shared_set", set())

        def __init__(self, name):
            super().__init__()
            self.name = name

        def __repr__(self):
            return self.name

    # Verify that the type was set correctly for all of these
    assert PropertyInit.a_list.type == list
    assert PropertyInit.a_dict.type == dict
    assert PropertyInit.a_set.type == set

    a = PropertyInit("A")
    b = PropertyInit("B")

    # Check that the storage variables haven't been created yet
    assert not hasattr(a, "_a_list")
    assert not hasattr(a, "_a_dict")
    assert not hasattr(a, "_a_set")
    assert not hasattr(a, "_shared_list")
    assert not hasattr(a, "_shared_dict")
    assert not hasattr(a, "_shared_set")
    assert not hasattr(b, "_a_list")
    assert not hasattr(b, "_a_dict")
    assert not hasattr(b, "_a_set")
    assert not hasattr(b, "_shared_list")
    assert not hasattr(b, "_shared_dict")
    assert not hasattr(b, "_shared_set")

    # Create the storage variables with the default value and verify
    for x in (a, b):
        x.a_list
        x.a_dict
        x.a_set
        x.shared_list
        x.shared_dict
        x.shared_set
    assert a._a_list == []
    assert a._a_dict == {}
    assert a._a_set == set()
    assert a._shared_list == []
    assert a._shared_dict == {}
    assert a._shared_set == set()
    assert b._a_list == []
    assert b._a_dict == {}
    assert b._a_set == set()
    assert b._shared_list == []
    assert b._shared_dict == {}
    assert b._shared_set == set()

    # Check that the getters return the default value
    assert a.a_list is a._a_list
    assert a.a_dict is a._a_dict
    assert a.a_set is a._a_set
    assert a.shared_list is a._shared_list
    assert a.shared_dict is a._shared_dict
    assert a.shared_set is a._shared_set
    assert b.a_list is b._a_list
    assert b.a_dict is b._a_dict
    assert b.a_set is b._a_set
    assert b.shared_list is b._shared_list
    assert b.shared_dict is b._shared_dict
    assert b.shared_set is b._shared_set

    # Passing a list as the default prevents all instances from sharing the mutable
    assert a.a_list is not b.a_list
    assert a.a_dict is not b.a_dict
    assert a.a_set is not b.a_set
    # Passing a mutable object as the default causes all instances to share the mutable
    assert a.shared_list is b.shared_list
    assert a.shared_dict is b.shared_dict
    assert a.shared_set is b.shared_set

    # Verify that the shared items are shared.
    a.shared_list.append("a")
    assert b.shared_list == ["a"]
    a.shared_dict["b"] = "c"
    assert b.shared_dict == {"b": "c"}
    a.shared_set.add("d")
    assert b.shared_set == set("d")
