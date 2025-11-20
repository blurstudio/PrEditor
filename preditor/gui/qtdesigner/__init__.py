"""
PYSIDE_DESIGNER_PLUGINS or PYQTDESIGNERPATH
"""
__all__ = ["QPyDesignerCustomWidgetCollection", "QPyDesignerCustomWidgetPlugin"]

import Qt  # noqa: E402

if Qt.IsPySide6:
    from PySide6.QtDesigner import (
        QPyDesignerCustomWidgetCollection,
        QPyDesignerCustomWidgetPlugin,
    )
elif Qt.IsPyQt6:
    from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
elif Qt.IsPySide2:
    from PySide2.QtDesigner import (
        QPyDesignerCustomWidgetCollection,
        QPyDesignerCustomWidgetPlugin,
    )
elif Qt.IsPyQt5:
    from PyQt5.QtDesigner import QPyDesignerCustomWidgetPlugin
