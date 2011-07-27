##
#	\namespace	blurdev.gui.designer.ColorPickerButton
#
#	\remarks	Defines a plugin file for the ColorPickerButton widget
#	
#	\author		beta@blur.com
#	\author		Blur Studio
#	\date		12/07/08
#

from PyQt4.QtDesigner 	import QPyDesignerCustomWidgetPlugin

class ColorPickerButtonPlugin( QPyDesignerCustomWidgetPlugin ):
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
        from blurdev.gui.widgets.colorwidgets import ColorPickerButton
        return ColorPickerButton( parent )
    
    def name( self ):
        return "ColorPickerButton"
    
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
        return "blurdev.gui.widgets.colorwidgets"
    
    def domXml( self ):
        xml = []
        xml.append( '<widget class="ColorPickerButton" name="ColorPickerButton"/>' )
        return '\n'.join( xml )

import blurdev.gui.designer
blurdev.gui.designer.register( 'ColorPickerButtonPlugin', ColorPickerButtonPlugin )
