from __future__ import absolute_import, print_function

import sys

import pytest
from Qt.QtWidgets import QApplication

from preditor.delayable_engine import DelayableEngine
from preditor.delayable_engine.delayables import Delayable, RangeDelayable
from preditor.scintilla.documenteditor import DocumentEditor

# TODO: Re-enable these tests once they work on the github runners
pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Test fails on gitrunner"
)


class RangeTestDelayable(RangeDelayable):
    key = 'range_test'

    def add_document(self, document):
        try:
            document.init_count += 1
        except AttributeError:
            document.init_count = 1

    def loop(self, document, line_num, line_end, value):
        return

    def remove_document(self, document):
        document.init_count -= 1


class ADelayable(Delayable):
    key = 'a_delayable'

    def add_document(self, document):
        try:
            document.init_count += 1
        except AttributeError:
            document.init_count = 1
        # enqueue a command so we can verify that remove_delayable removes it
        self.engine.enqueue(document, self.key)

    def remove_document(self, document):
        document.init_count -= 1


@pytest.fixture()
def engine():
    """Creates a test DelayableEngine and DocumentEditor.
    The DocumentEditor can be accessed by using `engine.test_doc`.
    """
    global app
    if not QApplication.instance():
        # These test require an initialized QApplication create one and ensure
        # it doesn't get garbage collected. Creating the app here prevents
        # segfaults when skipping this file on linux. We need to figure out
        # how to run these tests in github actions.
        app = QApplication([])

    engine = DelayableEngine('test_engine')
    engine.test_doc = DocumentEditor(None)
    engine.add_document(engine.test_doc)

    return engine


def test_add_delayable(engine):
    assert len(engine.delayables) == 0

    # Check that we can add a instance of Delayable
    delayable = RangeTestDelayable(engine)
    engine.add_delayable(delayable)
    assert len(engine.delayables) == 1

    # Adding a second delayable with the same key replaces the previous one
    delayable1 = RangeTestDelayable(engine)
    engine.add_delayable(delayable1)
    assert len(engine.delayables) == 1
    assert engine.delayables['range_test'] == delayable1

    # Check that if a invalid delayable key is passed a exception is raised
    with pytest.raises(KeyError):
        engine.add_delayable('undefined_key')
    assert len(engine.delayables) == 1

    # We can add a new Delayable instance if a valid key is passed
    engine.add_delayable('a_delayable')
    assert len(engine.delayables) == 2


@pytest.mark.parametrize(
    'args1,args2,merged',
    (
        # Smallest start should be used
        ((10, 100, 'a'), (25, 75, 'b'), (10, 100, 'b')),
        ((50, 100, 'a'), (25, 75, 'b'), (25, 100, 'b')),
        # Largest end should be used
        ((50, 60, 'a'), (25, 75, 'b'), (25, 75, 'b')),
        ((50, 100, 'a'), (60, 75, 'b'), (50, 100, 'b')),
        # None should always be used for end if passed
        ((50, 60, 'a'), (25, None, 'b'), (25, None, 'b')),
        ((50, None, 'a'), (25, 75, 'b'), (25, None, 'b')),
        ((50, None, 'a'), (25, None, 'b'), (25, None, 'b')),
    ),
)
def test_merge_args(engine, args1, args2, merged):
    delayable = RangeTestDelayable(engine)
    engine.add_delayable(delayable)

    engine.enqueue(engine.test_doc, 'range_test', *args1)
    args = engine.test_doc.delayable_info['range_test']
    # merge_args should not have been called yet, so args should be unchanged
    assert args == args1

    # Encueue the same key twice without looping will force a call of merge_args
    engine.enqueue(engine.test_doc, 'range_test', *args2)
    args = engine.test_doc.delayable_info['range_test']
    assert args == merged


def test_remove_documents(engine):
    """Check that a document can be removed and added correctly."""
    delayable = RangeTestDelayable(engine)
    engine.add_delayable(delayable)

    # Check that add_document was called originally
    assert len(engine.documents) == 1
    assert engine.test_doc.init_count == 1
    # Check that the delayable_engine was updated correctly
    assert engine.test_doc.delayable_engine.name == 'test_engine'

    # Check that remove_document was called
    engine.remove_document(engine.test_doc)
    assert len(engine.documents) == 0
    assert engine.test_doc.init_count == 0
    assert engine.test_doc.delayable_engine.name == 'default'

    # Check that add_document is called again
    engine.add_document(engine.test_doc)
    assert len(engine.documents) == 1
    assert engine.test_doc.init_count == 1
    assert engine.test_doc.delayable_engine.name == 'test_engine'


def test_remove_delayables(engine):
    """Check that a delayable can be added and removed correctly."""
    delayable = ADelayable(engine)
    engine.add_delayable(delayable)

    # Check that add_document was called originally
    assert len(engine.delayables) == 1
    assert engine.test_doc.init_count == 1
    assert 'a_delayable' in engine.test_doc.delayable_info
    # Removing a delayable doesn't remove the delay engine
    assert engine.test_doc.delayable_engine.name == 'test_engine'

    # Check that remove_document was called
    engine.remove_delayable(delayable)
    assert len(engine.delayables) == 0
    assert engine.test_doc.init_count == 0
    assert 'a_delayable' not in engine.test_doc.delayable_info
    assert engine.test_doc.delayable_engine.name == 'test_engine'

    # Check that add_document is called again
    engine.add_delayable(delayable)
    assert len(engine.delayables) == 1
    assert engine.test_doc.init_count == 1
    assert 'a_delayable' in engine.test_doc.delayable_info
    assert engine.test_doc.delayable_engine.name == 'test_engine'
