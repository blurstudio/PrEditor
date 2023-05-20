from __future__ import absolute_import, print_function

import time
import warnings
import weakref
from collections import OrderedDict

import six
from Qt import QtCompat
from Qt.QtCore import QObject, QTimer, Signal

from .delayables import Delayable

try:
    from collections.abc import MutableSet
except ImportError:
    # Due to the older versions of six installed by default with DCC's like
    # Maya 2020, we can't rely on six.moves.collections_abc, so handle
    # the py 2.7 import
    from collections import MutableSet


# https://stackoverflow.com/a/7829569
class OrderedSet(MutableSet):
    def __init__(self, values=()):
        self._od = OrderedDict().fromkeys(values)

    def __len__(self):
        return len(self._od)

    def __iter__(self):
        return iter(self._od)

    def __contains__(self, value):
        return value in self._od

    def add(self, value):
        self._od[value] = None

    def discard(self, value):
        self._od.pop(value, None)


class OrderedWeakrefSet(weakref.WeakSet):
    def __init__(self, values=()):
        super(OrderedWeakrefSet, self).__init__()
        self.data = OrderedSet()
        for elem in values:
            self.add(elem)


class DelayableEngine(QObject):
    """Provides a way for multiple DocumentEditors to run code over
    multiple Qt event loops in chunks preventing locking up the ui.

    Signals:
        processing_finished (int, float): Emitted when the engine finishes
            processing successfully.
    """

    _instance = {}
    processing_finished = Signal()

    def __init__(self, name, parent=None, interval=0):
        super(DelayableEngine, self).__init__()
        self.name = name
        self.documents = OrderedWeakrefSet()
        self.delayables = {}
        self.maxLoopTime = 0.01
        self.start_time = time.time()
        # It's likely we wont' finish processing all documents and all delayables
        # before we run out of time. These variables keep track of where we stopped.
        self.document_index = 0
        self.delayable_index = 0

        self.timer = QTimer(self)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.loop)

        # These values are reset when enqueue needs to start self.timer
        # Each of these lists have a item added when self.loop exits
        # (this can be it finished or ran out of time)
        # Number of documents that had a delayable.loop called on them this loop
        self.processed = []
        # Time spent processing delayables for this self.loop
        self.processing_time = []
        # Number of nonVisible items that were skipped for this self.loop
        self.skipped = []

    def __repr__(self):
        return '{}.{}("{}")'.format(
            self.__module__,
            self.__class__.__name__,
            self.name,
        )

    def __str__(self):
        return '{}("{}")'.format(self.__class__.__name__, self.name)

    def add_delayable(self, delayable):
        """Add a Delayable subclass instance for processing in this engine.

        Args:
            delayable (Delayable or str): A Delayable instance or the key identifier.
                If a Delayable instance is passed, it will replace any previous
                instances. If a string is passed it will not replace previous instance.

        Raises:
            KeyError: A invalid key identifier string was passed.
        """
        if isinstance(delayable, six.string_types):
            if delayable in self.delayables:
                # Don't replace the instance if a string is passed
                return
            for cls in Delayable._all_subclasses():
                if cls.key == delayable:
                    delayable = cls(self)
                    break
            else:
                raise KeyError('No Delayable found with key: "{}"'.format(delayable))
        elif delayable.key in self.delayables:
            # Remove the old delayable if it exists so we can replace it.
            self.remove_delayable(self.delayables[delayable.key])

        self.delayables[delayable.key] = delayable
        for document in self.documents:
            delayable.add_document(document)

    def add_document(self, document):
        self.documents.add(document)
        document.delayable_engine = self
        for delayable in self.delayables:
            self.delayables[delayable].add_document(document)

    def add_supported_delayables(self, name):
        """Add all valid Delayable subclasses that have name in their supports."""
        for delayable in Delayable._all_subclasses():
            if delayable.key not in self.delayables:
                if name in delayable.supports and delayable.key != 'invalid':
                    self.add_delayable(delayable(self))

    def delayable_enabled(self, delayable):
        """Returns True if delayable is currently added.

        Args:
            delayable (Delayable or str): A Delayable instance or the key identifier.

        Returns:
            bool: Is the given delayable installed for this engine.
        """
        if isinstance(delayable, Delayable):
            delayable = delayable.key
        return delayable in self.delayables

    def enqueue(self, document, key, *args):
        # Only add a item to be processed if we have a delayable that can
        # process the requested key.
        if key in self.delayables:
            # There is only ever one instance of a delayable class processed
            # If we already have a class enqueued, merge the arguments so we
            # don't end up loosing some processing.
            if key in document.delayable_info:
                args = self.delayables[key].merge_args(
                    document.delayable_info[key], args
                )
            document.delayable_info[key] = args
            if not self.timer.isActive():
                self.timer.start()
                self.processed = []
                self.processing_time = []
                self.skipped = []
            return True
        return False

    def expired(self):
        return time.time() - self.start_time > self.maxLoopTime

    @classmethod
    def instance(cls, name, parent=None, interval=0):
        """Returns a shared instance of DelayableEngine, creating the instance
        if needed.

        Args:
            name (str): The name of the delayable engine to get the instance of.
            parent (QWidget, optional): If a new instance is created, use this
                as its parent. Ignored otherwise.
            interval (int, optional): If a new instance is created, use this as
                its interval value. Defaults to zero.
        """
        if name not in cls._instance:
            cls._instance[name] = cls(name, parent=parent, interval=interval)
        return cls._instance[name]

    def loop(self):  # noqa C901
        self.start_time = time.time()
        documents = list(self.documents)
        # offset documents by the document_index so we can pickup where we left off
        documents = documents[self.document_index :] + documents[: self.document_index]

        count = 0
        skipped = 0
        finished = True
        first_loop = True
        while not self.expired():
            for document in documents:
                self.document_index += 1
                if self.document_index >= len(documents):
                    self.document_index = 0

                if not QtCompat.isValid(document):
                    if document in self.documents:
                        self.documents.remove(document)
                        print('Removing deleted document')
                    continue

                if not document.delayable_info:
                    continue

                if not document.isVisible() and first_loop:
                    skipped += 1
                    continue

                keys = list(document.delayable_info.keys())
                keys = keys[self.delayable_index :] + keys[: self.delayable_index]
                for key in keys:
                    self.delayable_index += 1
                    if self.delayable_index > len(keys):
                        self.delayable_index = 0

                    # delayable_info should only have keys for delayables we can access.
                    delayable = self.delayables[key]

                    args = document.delayable_info[key]
                    try:
                        args = delayable.loop(document, *args)
                    except Exception:
                        warnings.warn('Error processing {}, canceling it'.format(key))
                        del document.delayable_info[key]
                        raise
                    if args:
                        document.delayable_info[key] = args
                        # We need to process more items
                        finished = False
                    else:
                        del document.delayable_info[key]
                    count += 1
                    if self.expired():
                        self.processed.append(count)
                        self.processing_time.append(time.time() - self.start_time)
                        self.skipped.append(skipped)
                        return

            first_loop = False

        self.processed.append(count)
        self.processing_time.append(time.time() - self.start_time)
        self.skipped.append(skipped)
        if finished:
            # Nothing else to do for now, just exit
            self.timer.stop()
            self.processing_finished.emit()

    def remove_document(self, document):
        """Removes a document from being processed"""
        if document in self.documents:
            for delayable in self.delayables:
                self.delayables[delayable].remove_document(document)

            self.documents.remove(document)
            document.delayable_engine = type(self).instance('default')

    def remove_delayable(self, delayable):
        """Removes a Delayable subclass instance for processing in this engine.

        Args:
            delayable (Delayable or str): A Delayable instance or the key identifier.
                Remove this delayable from the current documents if it was added.
        """
        if isinstance(delayable, six.string_types):
            if delayable not in self.delayables:
                return
            delayable = self.delayables[delayable]
        if delayable:
            for document in self.documents:
                delayable.remove_document(document)
                # Stop processing this delayable if it's currently processing.
                try:
                    del document.delayable_info[delayable.key]
                except KeyError:
                    pass
            self.delayables.pop(delayable.key)

    def set_delayable_enabled(self, delayable, enabled):
        """Add or remove the delayable provided.

        Args:
            delayable (Delayable or str): A Delayable instance or the key identifier.
            enabled (bool): If True installs delayable, if False removes delayable.

        See Also:
            :py:meth:`DelayableEngine.add_delayable` and
            :py:meth:`DelayableEngine.remove_delayable`

        Raises:
            KeyError: A invalid key identifier string was passed.
        """
        if enabled:
            self.add_delayable(delayable)
        else:
            self.remove_delayable(delayable)
