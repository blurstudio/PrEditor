##
#	\namespace	blurdev.ide.delegates
#
#	\remarks	[desc::commented]
#	
#	\author		eric@blur.com
#	\author		Blur Studio
#	\date		05/23/11
#

from Qt.QtWidgets import QItemDelegate

class FilesystemDelegate( QItemDelegate ):
    def __init__( self, parent ):
        QItemDelegate.__init__( self, parent )
        
        self._currOverlay 	= None
        
    def drawDecoration( self, painter, option, rect, pixmap ):
        QItemDelegate.drawDecoartion( self, painter, option, rect, pixmap )
        
        # draw overlay icon
        if ( self._currOverlay ):
            painter.drawPixmap( rect, QPixmap(self._currOverlay) )
    
    def paint( self, painter, option, index ):
        # extract the filesystem information
        