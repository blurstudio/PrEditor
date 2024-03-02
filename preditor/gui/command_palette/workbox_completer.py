from __future__ import absolute_import

from Qt.QtWidgets import QCompleter

from .workbox_item_model import WorkboxFuzzyFilterProxyModel


class WorkboxCompleter(QCompleter):
    def __init__(self, *args, **kwargs):
        super(WorkboxCompleter, self).__init__(*args, **kwargs)
        # Set this to None to disable splitting of paths
        self.split_char = "/"
        # Create the proxy model that implemts fuzy searching
        self.proxyModel = WorkboxFuzzyFilterProxyModel(self)
        # Prevent the completer from removing results. This allows
        # us to always see the filtered results from the proxy model.
        self.setCompletionMode(self.UnfilteredPopupCompletion)

    def setModel(self, model):
        self.proxyModel.setSourceModel(model)
        super().setModel(self.proxyModel)

    def splitPath(self, path):
        if self.split_char:
            return path.split(self.split_char)
        return [path]

    def pathFromIndex(self, index):
        return self.model().pathFromIndex(index)
        # return self.proxyModel.sourceModel().pathFromIndex(index)

    def updatePattern(self, patternStr):
        self.proxyModel.setFuzzySearch(patternStr)
