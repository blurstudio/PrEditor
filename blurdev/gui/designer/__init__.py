##
#	\namespace	blurdev.gui.designer
#
#	\remarks	This package contains classes that expose blurdev widgets to the Qt Designer
#	
#	\author		beta@blur.com
#	\author		Blur Studio
#	\date		12/07/08
#

plugindef = """##
#	\\namespace	blurdev.gui.designer.%(class)s
#
#	\\remarks	Defines a plugin file for the %(class)s widget
#	
#	\\author		beta@blur.com
#	\\author		Blur Studio
#	\\date		12/07/08
#

from PyQt4.QtDesigner 	import QPyDesignerCustomWidgetPlugin

class %(class)sPlugin( QPyDesignerCustomWidgetPlugin ):
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
        from %(module)s import %(class)s
        return %(class)s( parent )
    
    def name( self ):
        return "%(class)s"
    
    def group( self ):
        return "%(group)s"
    
    def icon( self ):
        from PyQt4.QtGui import QIcon
        return QIcon( "%(icon)s" )
    
    def toolTip( self ):
        return ""
    
    def whatsThis( self ):
        return ""
    
    def isContainer( self ):
        return %(container)s
    
    def includeFile( self ):
        return "%(module)s"
    
    def domXml( self ):
        xml = []
        %(xmlContainer)s
        return '\\n'.join( xml )

import blurdev.gui.designer
blurdev.gui.designer.register( '%(class)sPlugin', %(class)sPlugin )
"""
# Provides basic container support. A widget like the AccordianWidget will require implementing a custom QDesignerContainerExtension.
# http://qt-project.org/doc/qt-4.8/qdesignercontainerextension.html
xmlContainerDef = """xml.append('<widget class="%(containerClass)s">')
        %(inside)s
        xml.append('</widget>')"""
# Used for non-container widgets and to fill in inside xmlContainerDef.
xmlRegularDef = """xml.append('<widget class="%(class)s" name="%(class)s"/>')"""

import glob, os, sys

from blurdev import osystem

def init():
    # load the installed modules
    import blurdev
    loadPlugins( blurdev.resourcePath( 'designer_plugins.xml' ) )
    
    # load the user modules
    loadPlugins( blurdev.prefPath( 'designer_plugins.xml' ) )
    
    # load any additional modules from the environment
    for key in os.environ:
        if ( key.startswith( 'BDEV_DESIGNERPLUG_' ) ):
            osplt = os.environ[key].split(',')
            if ( len(osplt) == 2 ):
                href 		= osplt[0]
                importPath 	= osplt[1]
            else:
                href		= osplt[0]
                importPath	= ''
            loadPlugins( href, importPath )
    
    # import the modules
    filenames = glob.glob( os.path.split( __file__ )[0] + '/*.py' )
    filenames.sort()
    for filename in filenames:
        modname = os.path.basename( filename ).split( '.' )[0]
        if ( modname != '__init__' ):
            fullname = 'blurdev.gui.designer.%s' % modname
            try:
                __import__( fullname )
            except:
                print 'Error loading %s' % fullname

def loadPlugins( filename, importPath = '' ):
    from blurdev.XML import XMLDocument
    doc = XMLDocument()
    
    # register the import path location
    if ( importPath ):
        importPath = osystem.expandvars(importPath)
        if ( os.path.exists(importPath) and not importPath in sys.path ):
            sys.path.insert(0,importPath)
    
    filename = osystem.expandvars(filename)
    
    if ( doc.load( filename ) ):
        
        blurdevpath = os.path.abspath( os.path.split( __file__ )[0] + '/../..' )
        
        for child in doc.root().children():
            # load an included module
            if ( child.nodeName == 'include' ):
                loadPlugins( child.attribute('href'), child.attribute('root') )
            
            # create a standard plugin
            else:
                createPlugin( child.attribute( "module" ), child.attribute( "class" ), child.attribute( "icon" ), child.attribute( "group", 'Blur Widgets' ), eval(child.attribute( 'container', 'False' )), child.attribute('containerClass', 'QWidget'))

def register( name, plugin ):
    import blurdev.gui.designer
    blurdev.gui.designer.__dict__[ name ] = plugin

def createPlugin( module, cls, icon = '', group = 'Blur Widgets', container = False, containerClass = '' ):
    options = { 'module': module, 'class': cls, 'icon': icon, 'group': group, 'container': container, 'containerClass': containerClass }
    if container:
        xmlCont = xmlRegularDef % options
        for container in containerClass.split(','):
            xmlCont = xmlContainerDef % {'containerClass': container, 'inside': xmlCont}
    else:
        xmlCont = xmlRegularDef
    options.update({'xmlContainer': xmlCont % options})
    filename = os.path.split( __file__ )[0] + '/%splugin.py' % str( cls ).lower()
    f = open( filename, 'w' )
    f.write( plugindef % options )
    f.close()
    