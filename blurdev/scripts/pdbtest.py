# import pdb
# from Qt import QtCore
#
#
# import blurdev.external
#
# class PdbOutput:
# 	def __init__(self):
# 		self._external = blurdev.external.External(['blurdev', 'showLogger'])
#
# 	def flush(self):
# 		pass
#
# 	def write( self, msg ):
# 		self._external.writeToPipe(msg)
#
# myStdOut = PdbOutput()
# mypdb = pdb.Pdb(stdout=myStdOut)
#
# def test():
# 	print('before')
# 	QtCore.pyqtRemoveInputHook()
# 	mypdb.set_trace()
##	QtCore.pyqtRestoreInputHook()
# 	print('after')


from __future__ import print_function


def stuff():
    for i in range(100):
        print(i)


import blurdev

print('starting test')

blurdev.debug.set_trace()
stuff()

print('ending test')
