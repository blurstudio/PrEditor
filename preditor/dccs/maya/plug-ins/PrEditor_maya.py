from __future__ import absolute_import

import maya.mel
from maya import OpenMayaUI, cmds

preditor_menu = None


def headless():
    """If true, no Qt gui elements should be used because python is running a
    QCoreApplication."""
    return bool(cmds.about(batch=True))

    # TODO: This is the old method for detecting batch mode. Remove this once
    # the above about command is vetted as working.
    # basename = os.path.splitext(os.path.basename(sys.executable).lower())[0]
    # return basename in ('mayabatch', 'mayapy')


def root_window():
    """Returns the main window of Maya as a Qt object to be used for parenting."""
    from Qt import QtCompat

    ptr = OpenMayaUI.MQtUtil.mainWindow()
    if ptr is not None:
        pointer = int(ptr)
        return QtCompat.wrapInstance(pointer)


def launch(ignored):
    """Show the PrEditor GUI and bring it into focus if it was minimized."""
    import preditor

    widget = preditor.launch()
    return widget


def initializePlugin(mobject):  # noqa: N802
    """Initialize the script plug-in"""
    global preditor_menu

    # If running headless, there is no need to build a gui and create the python logger
    if not headless():
        from Qt.QtWidgets import QApplication

        import preditor

        maya_ver = cmds.about(version=True).split(" ")[0]

        # Capture all stderr/out after the plugin is loaded. This makes it so
        # if the PrEditor GUI is shown, it will include all of the output. Also
        # tells PrEditor how to parent itself to the main window and save prefs.
        preditor.configure(
            # Set the core_name so preferences are saved per-maya version.
            "Maya-{}".format(maya_ver),
            # Tell PrEditor how to find the maya root window for parenting
            parent_callback=root_window,
            # Tell it how to check if running in batch mode
            headless_callback=headless,
        )

        # Detect Maya shutting down and ensure PrEditor's prefs are saved
        if QApplication.instance():
            QApplication.instance().aboutToQuit.connect(preditor.shutdown)

        # Add a new PrEditor menu with an item that launches PrEditor
        gmainwindow = maya.mel.eval("$temp1=$gMainWindow")
        preditor_menu = cmds.menu(label="PrEditor", parent=gmainwindow, tearOff=True)
        cmds.menuItem(
            label="Show",
            command=launch,
            sourceType="python",
            image=preditor.resourcePath('img/preditor.png'),
            parent=preditor_menu,
        )

        # TODO: Alternatively figure out how to add the launcher menuItem to a
        # pre-existing maya menu like next to the "Script Editor" in
        # "Windows -> General Editors"
        # https://github.com/chadmv/cvwrap/blob/master/scripts/cvwrap/menu.py#L18

        # menu = 'mainWindowMenu'
        # # Make sure the menu widgets exist first.
        # maya.mel.eval('ChaDeformationsMenu MayaWindow|{0};'.format(menu))
        # items = cmds.menu(menu, q=True, ia=True)
        # # print(items)
        # for item in items:
        #     menu_label = cmds.menuItem(item, q=True, label=True)
        #     # print(menu_label)
        #     if menu_label == "General Editors":
        #         # cmds.menuItem(parent=item, divider=True, dividerLabel='PrEditor' )
        #         cmds.menuItem(
        #             label="PrEditor",
        #             command=launch,
        #             sourceType='python',
        #             image=preditor.resourcePath('img/preditor.png'),
        #             parent=item,
        #         )


def uninitializePlugin(mobject):  # noqa: N802
    """Uninitialize the script plug-in"""
    import preditor

    # Remove the PrEditor Menu if it exists
    if preditor_menu and cmds.menu(preditor_menu, exists=True):
        cmds.deleteUI(preditor_menu, menu=True)

    # Close PrEditor making sure to save prefs
    preditor.core.shutdown()
