from __future__ import absolute_import

from Qt.QtWidgets import QTabWidget


class OneTabWidget(QTabWidget):
    """A QTabWidget that shows the close button only if there is more than one
    tab. If something removes the last tab, it will add a default tab if the
    default_tab method is implemented on a subclass. This is also used to create
    the first tab on showEvent.

    Subclasses can implement a `default_tab()` method. This should return the
    widget to add and the title of the tab to create if implemented.
    """

    def __init__(self, *args, **kwargs):
        super(OneTabWidget, self).__init__(*args, **kwargs)
        self.tabCloseRequested.connect(self.close_tab)

    def addTab(self, *args, **kwargs):  # noqa: N802
        ret = super(OneTabWidget, self).addTab(*args, **kwargs)
        self.update_closable_tabs()
        return ret

    def close_tab(self, index):
        self.removeTab(index)
        self.update_closable_tabs()

    def index_for_text(self, text):
        """Return the index of the tab with this text. Returns -1 if not found"""
        for i in range(self.count()):
            if self.tabText(i) == text:
                return i
        return -1

    def insertTab(self, *args, **kwargs):  # noqa: N802
        ret = super(OneTabWidget, self).insertTab(*args, **kwargs)
        self.update_closable_tabs()
        return ret

    def removeTab(self, index):  # noqa: N802
        super(OneTabWidget, self).removeTab(index)
        if hasattr(self, 'default_tab') and not self.count():
            self.addTab(*self.default_tab())
        self.update_closable_tabs()

    def showEvent(self, event):  # noqa: N802
        super(OneTabWidget, self).showEvent(event)
        # Force the creation of a default tab if defined
        if hasattr(self, 'default_tab') and not self.count():
            self.addTab(*self.default_tab())

    def update_closable_tabs(self):
        self.setTabsClosable(self.count() != 1)
