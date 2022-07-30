from __future__ import absolute_import, print_function

import collections

from ..weakref import WeakList


class Manager(collections.deque):
    """Stores all of the data from the stdout/stderr writes. You can iterate over this
    object to see all of the (msg, state) calls that have been written to it up to the
    maxlen specified when constructing it.

    Args:
        maxlen (int, optional): The maximum number of raw writes to store. If this is
            exceeded, the oldest writes are discarded.

    Properties:
        store_writes (bool): Set this to False if you no longer want write calls to
            store on the manager.
    """

    def __init__(self, maxlen=10000):
        super(Manager, self).__init__(maxlen=maxlen)
        self.callbacks = WeakList()
        self.store_writes = True

    def add_callback(self, callback, replay=False, disable_writes=False, clear=False):
        """Add a callable that will be called every time write is called.

        Args:
            callback (callable): A callable object that takes two arguments. It must
                take two arguments (msg, state). See write for more details.
            replay (bool, optional): If True, then iterate over all the stored writes
                and pass them to callback. This is useful for when you are initializing
                a gui and want to include all previous prints.
            disable_writes (bool, optional): Set store_writes to False if this is True.
            clear (bool, optional): Clear the stored history on this object.
        """
        self.callbacks.append(callback)

        if replay:
            # Replay the existing prints into the console.
            for msg, state in self:
                callback(msg, state)

        if disable_writes:
            # Disable storing data in the buffer. buffer.write calls will now
            # directly write to console so there is no reason to duplicate the
            # data to the buffer.
            self.store_writes = False

        if clear:
            self.clear()

    def remove_callback(self, callback):
        self.callbacks.remove(callback)

    def get_value(self, fmt="[{state}:{msg}]"):
        return ''.join([fmt.format(msg=d[0], state=d[1]) for d in self])

    def write(self, msg, state):
        """Adds the written text to the manager and passes it to any attached callbacks.

        Args:
            msg (str): The text to be written.
            state: A identifier for how the text is to be written. For example if this
                write is coming from sys.stderr this will likely be set to
                ``preditor.stream.STDERR``.
        """
        if self.store_writes:
            self.append((msg, state))

        for callback in self.callbacks:
            callback(msg, state)
