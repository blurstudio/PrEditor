##
#	\namespace	blurdev.gui.designer.FilePickerWidget
#
#	\remarks	Defines a plugin file for the FilePickerWidget widget
#	
#	\author		beta@blur.com
#	\author		Blur Studio
#	\date		12/07/08
#

from PyQt4.QtDesigner 	import QPyDesignerCustomWidgetPlugin

class FilePickerWidgetPlugin( QPyDesignerCustomWidgetPlugin ):
    def __init__( self, parent = None ):
        QPyDesignerCustomWidgetPlugin.__init__( self )
        
        self.initialized = False
    
    def initialize( self, core ):
        if ( self.initialized ):
            return
        
        self.initialized = True
    
    def isInitialized( self ):
        return self.initialized
    
    def createWidget( self, parent ):
        from blurdev.gui.widgets.filepickerwidget import FilePickerWidget
        return FilePickerWidget( parent )
    
    def name( self ):
        return "FilePickerWidget"
    
    def group( self ):
        return "Blur Widgets"
    
    def icon( self ):
        from PyQt4.QtGui import QIcon
        return QIcon( "" )
    
    def toolTip( self ):
        return ""
    
    def whatsThis( self ):
        return ""
    
    def isContainer( self ):
        return False
    
    def includeFile( self ):
        return "blurdev.gui.widgets.filepickerwidget"
    
    def domXml( self ):
        xml = []
        xml.append( '<widget class="FilePickerWidget" name="FilePickerWidget"/>' )
        return '\n'.join( xml )

import blurdev.gui.designer
blurdev.gui.designer.register( 'FilePickerWidgetPlugin', FilePickerWidgetPlugin )
