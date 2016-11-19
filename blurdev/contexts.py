import os
import shutil
import tempfile


class TempFilesContext(object):
    """ Context to create multiple temp files and directories that will be removed.
	
	This class is used to manage generation of multiple temp files and directories.
	The files and directories created by makeTempDirectory and makeTempFile will
	be removed once this contex exits. 
	
	Keyed mode returns the same object if one of the make functions is called twice
	with the same key.
	
	Args:
		keyed (bool): Enables Keyed mode.
		defaultDir (str|None): If not None(the default) this is passed to tempfile
			functions as the dir kwarg if that kwarg is not provided in the call.
	"""

    def __init__(self, keyed=True, defaultDir=None):
        self.keyed = keyed
        self.defaultDir = defaultDir
        self._tempDirs = {}
        self._tempFiles = {}

    def makeTempDirectory(self, *args, **kwargs):
        """ Creates a temporary directory and returns its file path.
		
		This directory and all of its contents are removed on exit.
		args and kwargs are passed to tempfile.NamedTemporaryFile after the 
		"key" kwarg has been removed. If dir is not provided in kwargs and 
		self.defaultDir is set, it will be added to kwargs.
		
		Args:
			key(str): If in keyed mode only one directory will be created
				for any key value. Any future calls to this function with
				the same key will return the same directory. If keyed is
				False, this will always return a new directory name. The
				default key is 'default'.
		
		Returns:
			str: The full path to the temporary directory.
		"""
        if self.keyed:
            key = kwargs.pop('key', 'default')
        else:
            # This is not keyed, so generate a new key each time its called
            key = len(self._tempDirs)

        if key not in self._tempDirs:
            # If a defaultDir was provided, make sure its included
            if self.defaultDir is not None and 'dir' not in kwargs:
                kwargs['dir'] = self.defaultDir
                print 'makeTempDirectory adding defaultDir', self.defaultDir

            tempDir = tempfile.mkdtemp(*args, **kwargs)
            self._tempDirs[key] = tempDir
        return self._tempDirs[key]

    def makeTempFile(self, *args, **kwargs):
        """ Creates a tempfile using tempfile.mkstemp and returns the path to the file.
		
		This file will only be valid till the context exits.
		args and kwargs are passed to tempfile.mkstemp after the "key" kwarg has been 
		removed. If dir is not provided in kwargs and self.defaultDir is set, it will 
		be added to kwargs.
		
		Args:
			key(str): If in keyed mode only one directory will be created
				for any key value. Any future calls to this function with
				the same key will return the same directory. If keyed is
				False, this will always return a new directory name. The
				default key is 'default'.
		
		Returns:
			str: the full path to the temporary file.
		"""
        if self.keyed:
            key = kwargs.pop('key', 'default')
        else:
            # This is not keyed, so generate a new key each time its called
            key = len(self._tempFiles)

        if key not in self._tempFiles:
            # If a defaultDir was provided, make sure its included
            print 'DEFAULT DIR', [self.defaultDir, kwargs]
            if self.defaultDir is not None and 'dir' not in kwargs:
                kwargs['dir'] = self.defaultDir
                print 'makeTempFile adding defaultDir', self.defaultDir

            tempFile = tempfile.mkstemp(*args, **kwargs)
            self._tempFiles[key] = tempFile
        return self._tempFiles[key][1]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # Remove any created folders from disk and their contents
        for tempDir in self._tempDirs.values():
            shutil.rmtree(tempDir)
        self._tempDirs = {}
        # Remove any created temp files
        for tempFile in self._tempFiles.values():
            print tempFile
            os.close(tempFile[0])
            os.remove(tempFile[1])
        self._tempFiles = {}
