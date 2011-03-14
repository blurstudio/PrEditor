##
# 	\namespace	blurdev.progress
#
# 	\remarks	Creates a simple system for running quick and easy sectional based progress feedback for users
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		03/14/11
#
# 	\example	running a progress response with the blurdev.progress system
#
# 				|from blurdev import progress
# 				|import time # used for sleep example
# 				|from PyQt4.QtGui import QMessageBox
# 				|
# 				|# create dummy data
# 				|oldsoftware = range(50)
# 				|newsoftware = range(60)
# 				|
# 				|# setup the progress sections before processing data
# 				|isect = progress.addSection( 'Collecting Software Install Info', count = len(newsoftware), allowsCancel = True )
# 				|usect = progress.addSection( 'Uninstalling Old Software', count = len(oldsoftware))
# 				|bsect = progress.addSection( 'Installing New Software', count = len(newsoftware) )
# 				|
# 				|# start the progress
# 				|progress.start()
# 				|
# 				|# collect software info (Section 01)
# 				|for i in range(len(newsoftware)):
# 				|	# do something with new software (sleeping as example)
# 				|	time.sleep(0.1)
# 				|
# 				|	# increment the section
# 				|	isect.increment()
# 				|
# 				|	# check if the user cancelled
# 				|	if ( isect.cancelled() ):
# 				|		isect.acceptCancel()
# 				|		break
# 				|
# 				|# make sure we have not cancelled
# 				|if ( not isect.cancelled() ):
# 				|	# uninstall old software (Section 02)
# 				|	for i in range(len(oldsoftware)):
# 				|		# do something with old software (sleeping as example)
# 				|		time.sleep(0.1)
# 				|
# 				|		# increment the section
# 				|		usect.increment()
# 				|
# 				|	# install new software (Section 03)
# 				|	for i in range(len(newsoftware)):
# 				|		# do something with the new software (sleeping as example)
# 				|		time.sleep(0.1)
# 				|
# 				|		# simulate an error
# 				|		if ( i == (len(newsoftware) - 1) and QMessageBox.question( None, 'Simulate Error', 'Simulate Error?', QMessageBox.Yes | QMessageBox.No ) == QMessageBox.Yes ):
# 				|			bsect.setErrorText( 'An Unknown Error Has Occurred' )
# 				|			break
# 				|		else:
# 				|			bsect.increment()
# 				|
# 				|	print bsect.errored()

from blurdev.gui.dialogs.multiprogressdialog import MultiProgressDialog, ProgressSection

from PyQt4.QtCore import Qt
import blurdev

_dialog = MultiProgressDialog(blurdev.core.rootWindow())
_dialog.setAttribute(Qt.WA_DeleteOnClose, False)


def addSection(name, count=100, value=-1, allowsCancel=False):
    return _dialog.addSection(name, count=count, value=value, allowsCancel=allowsCancel)


def clear():
    _dialog.clear()


def finish():
    _dialog.finish()


def start(title='Progress'):
    _dialog.setWindowTitle(title)
    _dialog.update()
    _dialog.show()


def section(name):
    return _dialog.section(name)


_dialog.closed.connect(clear)
