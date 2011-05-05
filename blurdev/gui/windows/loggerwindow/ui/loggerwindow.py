# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'loggerwindow.ui'
#
# Created: Mon Apr 04 19:03:03 2011
#      by: PyQt4 UI code generator snapshot-4.7.1-5014f7c72a58
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(485, 367)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(180, 179, 182))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(150, 149, 151))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(80, 79, 80))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(31, 31, 31))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(126, 141, 147))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(180, 179, 182))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(150, 149, 151))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(80, 79, 80))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(31, 31, 31))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(126, 141, 147))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(180, 179, 182))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(150, 149, 151))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(80, 79, 80))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(60, 59, 60))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(178, 180, 191))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.HighlightedText, brush)
        brush = QtGui.QBrush(QtGui.QColor(120, 119, 121))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, brush)
        MainWindow.setPalette(palette)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        self.uiMenuBar = QtGui.QMenuBar(MainWindow)
        self.uiMenuBar.setGeometry(QtCore.QRect(0, 0, 485, 21))
        self.uiMenuBar.setObjectName("uiMenuBar")
        self.uiDebugMENU = QtGui.QMenu(self.uiMenuBar)
        self.uiDebugMENU.setObjectName("uiDebugMENU")
        self.uiScriptingMENU = QtGui.QMenu(self.uiMenuBar)
        self.uiScriptingMENU.setObjectName("uiScriptingMENU")
        self.uiFileMENU = QtGui.QMenu(self.uiMenuBar)
        self.uiFileMENU.setObjectName("uiFileMENU")
        self.uiHelpMENU = QtGui.QMenu(self.uiMenuBar)
        self.uiHelpMENU.setObjectName("uiHelpMENU")
        self.menu_Run = QtGui.QMenu(self.uiMenuBar)
        self.menu_Run.setObjectName("menu_Run")
        MainWindow.setMenuBar(self.uiMenuBar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.uiSaveLogACT = QtGui.QAction(MainWindow)
        self.uiSaveLogACT.setObjectName("uiSaveLogACT")
        self.uiDebugLevel0ACT = QtGui.QAction(MainWindow)
        self.uiDebugLevel0ACT.setCheckable(True)
        self.uiDebugLevel0ACT.setObjectName("uiDebugLevel0ACT")
        self.uiDebugLevel1ACT = QtGui.QAction(MainWindow)
        self.uiDebugLevel1ACT.setCheckable(True)
        self.uiDebugLevel1ACT.setObjectName("uiDebugLevel1ACT")
        self.uiDebugLevel2ACT = QtGui.QAction(MainWindow)
        self.uiDebugLevel2ACT.setCheckable(True)
        self.uiDebugLevel2ACT.setObjectName("uiDebugLevel2ACT")
        self.uiDebugLevel3ACT = QtGui.QAction(MainWindow)
        self.uiDebugLevel3ACT.setCheckable(True)
        self.uiDebugLevel3ACT.setObjectName("uiDebugLevel3ACT")
        self.uiNoDebugACT = QtGui.QAction(MainWindow)
        self.uiNoDebugACT.setCheckable(True)
        self.uiNoDebugACT.setObjectName("uiNoDebugACT")
        self.uiDebugLowACT = QtGui.QAction(MainWindow)
        self.uiDebugLowACT.setCheckable(True)
        self.uiDebugLowACT.setObjectName("uiDebugLowACT")
        self.uiDebugMidACT = QtGui.QAction(MainWindow)
        self.uiDebugMidACT.setCheckable(True)
        self.uiDebugMidACT.setObjectName("uiDebugMidACT")
        self.uiDebugHighACT = QtGui.QAction(MainWindow)
        self.uiDebugHighACT.setCheckable(True)
        self.uiDebugHighACT.setObjectName("uiDebugHighACT")
        self.uiClearLogACT = QtGui.QAction(MainWindow)
        self.uiClearLogACT.setObjectName("uiClearLogACT")
        self.uiNewScriptACT = QtGui.QAction(MainWindow)
        self.uiNewScriptACT.setObjectName("uiNewScriptACT")
        self.uiOpenScriptACT = QtGui.QAction(MainWindow)
        self.uiOpenScriptACT.setObjectName("uiOpenScriptACT")
        self.uiRunScriptACT = QtGui.QAction(MainWindow)
        self.uiRunScriptACT.setObjectName("uiRunScriptACT")
        self.uiHintingEnabledACT = QtGui.QAction(MainWindow)
        self.uiHintingEnabledACT.setCheckable(True)
        self.uiHintingEnabledACT.setChecked(True)
        self.uiHintingEnabledACT.setObjectName("uiHintingEnabledACT")
        self.uiGotoErrorACT = QtGui.QAction(MainWindow)
        self.uiGotoErrorACT.setObjectName("uiGotoErrorACT")
        self.uiResetPathsACT = QtGui.QAction(MainWindow)
        self.uiResetPathsACT.setObjectName("uiResetPathsACT")
        self.uiSdkBrowserACT = QtGui.QAction(MainWindow)
        self.uiSdkBrowserACT.setObjectName("uiSdkBrowserACT")
        self.uiRunLineACT = QtGui.QAction(MainWindow)
        self.uiRunLineACT.setObjectName("uiRunLineACT")
        self.uiRunAllACT = QtGui.QAction(MainWindow)
        self.uiRunAllACT.setObjectName("uiRunAllACT")
        self.uiClearWorkspaceACT = QtGui.QAction(MainWindow)
        self.uiClearWorkspaceACT.setObjectName("uiClearWorkspaceACT")
        self.uiRunSelectedACT = QtGui.QAction(MainWindow)
        self.uiRunSelectedACT.setObjectName("uiRunSelectedACT")
        self.uiDebugMENU.addAction(self.uiNoDebugACT)
        self.uiDebugMENU.addSeparator()
        self.uiDebugMENU.addAction(self.uiDebugLowACT)
        self.uiDebugMENU.addAction(self.uiDebugMidACT)
        self.uiDebugMENU.addAction(self.uiDebugHighACT)
        self.uiDebugMENU.addSeparator()
        self.uiDebugMENU.addAction(self.uiGotoErrorACT)
        self.uiDebugMENU.addAction(self.uiResetPathsACT)
        self.uiScriptingMENU.addAction(self.uiNewScriptACT)
        self.uiScriptingMENU.addAction(self.uiOpenScriptACT)
        self.uiScriptingMENU.addSeparator()
        self.uiScriptingMENU.addAction(self.uiRunScriptACT)
        self.uiFileMENU.addAction(self.uiHintingEnabledACT)
        self.uiFileMENU.addSeparator()
        self.uiFileMENU.addAction(self.uiSaveLogACT)
        self.uiFileMENU.addAction(self.uiClearLogACT)
        self.uiHelpMENU.addAction(self.uiSdkBrowserACT)
        self.menu_Run.addAction(self.uiRunSelectedACT)
        self.menu_Run.addAction(self.uiRunAllACT)
        self.uiMenuBar.addAction(self.uiScriptingMENU.menuAction())
        self.uiMenuBar.addAction(self.uiDebugMENU.menuAction())
        self.uiMenuBar.addAction(self.menu_Run.menuAction())
        self.uiMenuBar.addAction(self.uiFileMENU.menuAction())
        self.uiMenuBar.addAction(self.uiHelpMENU.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QtGui.QApplication.translate(
                "MainWindow", "Command Logger", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugMENU.setTitle(
            QtGui.QApplication.translate(
                "MainWindow", "&Debugging", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiScriptingMENU.setTitle(
            QtGui.QApplication.translate(
                "MainWindow", "&File", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiFileMENU.setTitle(
            QtGui.QApplication.translate(
                "MainWindow", "&Options", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiHelpMENU.setTitle(
            QtGui.QApplication.translate(
                "MainWindow", "Help", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.menu_Run.setTitle(
            QtGui.QApplication.translate(
                "MainWindow", "&Run", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiSaveLogACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Save Log...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugLevel0ACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Level 0", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugLevel1ACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Level 1", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugLevel2ACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Level 2", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugLevel3ACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Level 3", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiNoDebugACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Disabled", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugLowACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Low Level", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugMidACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Mid Level", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiDebugHighACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&High Level", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiClearLogACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Clear Log", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiNewScriptACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&New Script", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiNewScriptACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Ctrl+N", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiOpenScriptACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Open Script...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiOpenScriptACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Ctrl+O", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunScriptACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "&Run Script...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunScriptACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "F5", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiHintingEnabledACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Use &Auto-Complete", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiGotoErrorACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Goto Error...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiGotoErrorACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Ctrl+G", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiResetPathsACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Reset Paths", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiSdkBrowserACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "SDK Help", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiSdkBrowserACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "F1", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunLineACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Run Line...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunLineACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Enter", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunAllACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Run All...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunAllACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Ctrl+Enter", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiClearWorkspaceACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Clear Workspace...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunSelectedACT.setText(
            QtGui.QApplication.translate(
                "MainWindow", "Run Selected...", None, QtGui.QApplication.UnicodeUTF8
            )
        )
        self.uiRunSelectedACT.setShortcut(
            QtGui.QApplication.translate(
                "MainWindow", "Shift+Return", None, QtGui.QApplication.UnicodeUTF8
            )
        )
