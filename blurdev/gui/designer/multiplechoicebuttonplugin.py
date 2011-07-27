##
#	\namespace	blurdev.gui.designer.MultipleChoiceButton
#
#	\remarks	Defines a plugin file for the MultipleChoiceButton widget
#	
#	\author		beta@blur.com
#	\author		Blur Studio
#	\date		12/07/08
#

from PyQt4.QtDesigner 	import QPyDesignerCustomWidgetPlugin

class MultipleChoiceButtonPlugin( QPyDesignerCustomWidgetPlugin ):
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
        from blurdev.gui.widgets.multiplechoicebutton import MultipleChoiceButton
        return MultipleChoiceButton( parent )
    
    def name( self ):
        return "MultipleChoiceButton"
    
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
        return "blurdev.gui.widgets.multiplechoicebutton"
    
    def domXml( self ):
        xml = []
        xml.append( '<widget class="MultipleChoiceButton" name="MultipleChoiceButton"/>' )
        return '\n'.join( xml )

import blurdev.gui.designer
blurdev.gui.designer.register( 'MultipleChoiceButtonPlugin', MultipleChoiceButtonPlugin )
