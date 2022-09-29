from preditor.gui.level_buttons import LazyMenu


class GroupTabMenu(LazyMenu):
    """A menu listing all tabs of GroupTabWidget and their child GroupedTabWidget
    tabs. When selecting one of the GroupedTabWidget tab, it will make that tab
    the current tab and give it focus.
    """

    def __init__(self, manager, parent=None):
        super(GroupTabMenu, self).__init__(parent=parent)
        self.manager = manager
        self.triggered.connect(self.focus_tab)

    def refresh(self):
        self.clear()
        for group in range(self.manager.count()):
            # Create a "header" for the group tabs
            self.addSeparator()
            act = self.addAction(self.manager.tabText(group))
            act.setEnabled(False)
            self.addSeparator()

            # Add all of this group tab's tabs
            tab_widget = self.manager.widget(group)
            for index in range(tab_widget.count()):
                act = self.addAction('  {}'.format(tab_widget.tabText(index)))
                act.setProperty('info', (group, index))

    def focus_tab(self, action):
        group, index = action.property('info')
        self.manager.setCurrentIndex(group)
        tab_widget = self.manager.widget(group)
        tab_widget.setCurrentIndex(index)
        widget = tab_widget.widget(index)
        widget.setFocus()
