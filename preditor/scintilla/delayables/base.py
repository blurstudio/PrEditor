from __future__ import absolute_import, print_function

from Qt.QtCore import QObject


class Delayable(QObject):
    key = 'invalid'
    supports = ('ide', 'workbox')

    def __init__(self, engine):
        self.engine = engine
        super(Delayable, self).__init__()

    @classmethod
    def _all_subclasses(cls):
        return cls.__subclasses__() + [
            g for s in cls.__subclasses__() for g in s._all_subclasses()
        ]

    def add_document(self, document):
        pass

    def loop(self, document, *args):
        return

    def merge_args(self, args1, args2):
        return args2

    def remove_document(self, document):
        pass


class RangeDelayable(Delayable):
    """Delayable designed to take a start and stop range as its first arguments."""

    def merge_args(self, args1, args2):
        """Uses the lowest start argument value. The end argument returns None if
        one of them is None otherwise the largest is returned. All other arguments
        of from args2 are used.

        Args:
            args1 (tuple): The old arguments.
            args2 (tuple): The new arguments.

        Returns:
            tuple: args2 with its first two arguments modified to the largest range.
        """
        start1 = args1[0]
        start2 = args2[0]
        start = min(start1, start2)

        end1 = args1[1]
        end2 = args2[1]
        if end1 is None or end2 is None:
            # Always prefer None for the end. It indicates that we want to
            # go to the end of the document.
            end = None
        else:
            end = max(end1, end2)
        return (start, end) + args2[2:]


class SearchDelayable(Delayable):
    def loop(self, document, find_state):
        start, end = document.find_text(find_state)
        if find_state.wrapped:
            # once we have wrapped, disable wrap
            find_state.wrap = False
        if start != -1:
            self.text_found(document, start, end, find_state)
            return (find_state,)

    def search_from_position(self, document, find_state, position, *args):
        if position is None:
            position = document.positionFromLineIndex(*document.getCursorPosition())
        # Start searching from position, wrap past the end and stop where we started
        find_state.start_pos = position
        find_state.start_pos_original = position
        find_state.wrap = True
        find_state.wrapped = False
        self.engine.enqueue(document, self.key, find_state, *args)

    def text_found(self, document, start, end, find_state):
        """Called each time text is found."""
        raise NotImplementedError('SearchDelayable.text_found should be subclassed.')
