from __future__ import absolute_import

from Qt.QtWidgets import QCompleter


class WorkboxCompleter(QCompleter):
    def __init__(self, *args, **kwargs):
        super(WorkboxCompleter, self).__init__(*args, **kwargs)
        # Set this to None to disable splitting of paths
        self.split_char = "/"

    def splitPath(self, path):
        if self.split_char:
            return path.split(self.split_char)
        return [path]

    def pathFromIndex(self, index):
        return self.model().pathFromIndex(index)
