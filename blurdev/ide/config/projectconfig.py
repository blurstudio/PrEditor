##
# 	\namespace	blurdev.ide.config.projectconfig
#
# 	\remarks	Sets up project configurations for the IDE system
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from PyQt4.QtGui import QTreeWidget


class ProjectConfig(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)

        self.setColumnCount(2)

        self.setHeaderLabels(['Name', 'Path'])

        # load the project types

        from PyQt4.QtCore import Qt, QSize

        from PyQt4.QtGui import QTreeWidgetItem, QIcon

        from blurdev.ide.ideproject import ProjectType, IdeProject

        import os.path

        path = os.path.split(__file__)[0]

        for typ in ProjectType.labels():

            default = QIcon(path + '/img/%s.png' % typ)

            item = QTreeWidgetItem([typ])

            item.setIcon(0, default)

            item.setSizeHint(0, QSize(250, 18))

            for proj in IdeProject.projectsByType(ProjectType.valueByLabel(typ)):

                pitem = QTreeWidgetItem([proj.name(), proj.path()])

                icon = QIcon(proj.icon())

                if icon.isNull():

                    icon = default

                pitem.setIcon(0, icon)

                pitem.setSizeHint(0, QSize(250, 18))

                item.addChild(pitem)

            self.addTopLevelItem(item)
