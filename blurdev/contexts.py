import sys
import os
import shutil
import tempfile
import errno
import time
import blurdev

# Note: If a different version of python is launched importing pre-compiled modules
# could cause a exception. For example, MotionBuilder 2016 has python 2.7.6 embeded,
# while at blur we currently have python 2.7.3 installed externally. Also applications
# like Maya 2016 compile python with newer versions of Visual Studio than normal which
# also causes problems.
import blurdev.debug
import traceback

# If possible use blur.Stone's isRunning. It works in Maya 2016 without needing to
# compile a special build of psutil. If neither psutil or blur.Stone is installed
# monitorForCrash will not be launched and temp files will be orphaned if python
# is killed by a external process.
try:
    # If Stone is not importable monitorForCrash for clash will not be used
    import blur.Stone as Stone
except ImportError:
    Stone = None
try:
    import psutil
except ImportError:
    psutil = None


def monitorForCrash(pid, conn):
    """ Multiprocessing function used to clean up temp files if the parent process is killed.
	"""
    # Note: importing inside this function can cause dll errors when running inside a DCC.
    try:
        tempFiles = []
        tempDirs = []
        print '[monitorForCrash] Checking pid', pid, (Stone, psutil)
        while (Stone and Stone.isRunning(pid)) or psutil and psutil.pid_exists(pid):
            try:
                if conn.poll():
                    data = conn.recv()
                    if data[0] == 'tempFile':
                        tempFiles.append(data[1])
                        print '[monitorForCrash] Adding tempFile', data[1]
                        # Check for more data instead of sleeping
                        continue
                    elif data[0] == 'tempDir':
                        tempDirs.append(data[1])
                        print '[monitorForCrash] Adding tempDir', data[1]
                        # Check for more data instead of sleeping
                        continue
                    elif data[0] == 'finished':
                        print '[monitorForCrash] Parent process is done, exiting without doing anything'
                        return
            except IOError as e:
                if e.errno == 109:
                    # The pipe has been ended, assume the parent process was killed
                    print '[monitorForCrash] IOError 109'
                    break
            time.sleep(1)

        print '[monitorForCrash] Removing tempFiles', tempFiles
        print '[monitorForCrash] Removing tempDirs', tempDirs
        # Remove any created folders from disk and their contents
        for tempDir in tempDirs:
            shutil.rmtree(tempDir, ignore_errors=True)
        # Remove any created temp files
        for tempFile in tempFiles:
            try:
                os.remove(tempFile)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    print '[monitorForCrash] File already deleted', e.message, tempFile
    except:
        traceback.print_exc()
        time.sleep(20)
        raise


class TempFilesContext(object):
    """ Context to create multiple temp files and directories that will be removed.
	
	This class is used to manage generation of multiple temp files and directories.
	The files and directories created by makeTempDirectory and makeTempFile will
	be removed once this contex exits. 
	
	Keyed mode returns the same object if one of the make functions is called twice
	with the same key.
	
	Note:
		The crashMonitor option uses multiprocessing to monitor if the main python
		module was killed. Because of how multiprocessing works on windows, if you
		used a script when launching python you need to make sure that the main 
		module can be safely imported by a new Python interpreter without causing 
		unintended side effects (such as calling TempFilesContext(crashMonitor=True)).
		Simply put, make sure you use in your scripts(if __name__ == '__main__':)
		See https://docs.python.org/2/library/multiprocessing.html#windows search 
		for "Safe importing of main module" for more info.
	
	Args:
		keyed (bool): Enables Keyed mode. Defaults to True.
		defaultDir (str|None): If not None(the default) this is passed to tempfile
			functions as the dir kwarg if that kwarg is not provided in the call.
		crashMonitor (bool): If True(default), use multiprocessing to launch a watcher 
			process if python is killed by some external process while inside this 
			context this external process will remove all temp files created by the 
			context.
		pythonw (bool): If True multiprocessing.set_executable will be set to 
			pythonw.exe. If False (default) it will be set to python.exe. If False 
			the print statements in the monitorForCrash() child process appear to 
			be redirected back to the parent process. This is useful for debugging.
	"""

    def __init__(self, keyed=True, defaultDir=None, crashMonitor=True, pythonw=False):
        self.keyed = keyed
        self.defaultDir = defaultDir
        self._tempDirs = {}
        self._tempFiles = {}
        self.crashMonitor = crashMonitor

        if self.crashMonitor:
            if Stone or psutil:
                import multiprocessing
                from multiprocessing import Process, Pipe

                self.pipe, child_conn = Pipe()
                pid = os.getpid()
                # If python is embeded in a application multiprocessing will launch a new
                # instance of that instead of python, so force it to run python.
                multiprocessing.set_executable(blurdev.osystem.pythonPath(pyw=pythonw))

                # multiprocessing requires sys.argv so manually create it if it doesn't already exist
                if not hasattr(sys, 'argv'):
                    sys.argv = ['']
                # Some applications like MotionBuilder break multiprocessing with their sys.argv values.
                argv = sys.argv
                try:
                    sys.argv = ['']
                    p = Process(target=monitorForCrash, args=(pid, child_conn))
                    p.start()
                finally:
                    # Restore the original sys.argv
                    sys.argv = argv
            else:
                self.crashMonitor = False
                print 'blur.Stone or psutil not installed crashMonitor disabled.'

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
            if self.crashMonitor:
                self.pipe.send(('tempDir', tempDir))
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

        closeHandle = kwargs.pop('closeHandle', False)

        if key not in self._tempFiles:
            # If a defaultDir was provided, make sure its included
            print 'DEFAULT DIR', [self.defaultDir, kwargs]
            if self.defaultDir is not None and 'dir' not in kwargs:
                kwargs['dir'] = self.defaultDir
                print 'makeTempFile adding defaultDir', self.defaultDir

            tempFile = tempfile.mkstemp(*args, **kwargs)
            self._tempFiles[key] = tempFile
            if self.crashMonitor:
                self.pipe.send(('tempFile', tempFile[1]))
            if closeHandle:
                os.close(tempFile[0])
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
            try:
                os.close(tempFile[0])
            except OSError as e:
                print 'Problem closing tempfile', e, e.message
            try:
                os.remove(tempFile[1])
            except OSError as e:
                if e.errno == errno.ENOENT:
                    print 'File already deleted', e.message
        self._tempFiles = {}
        if self.crashMonitor:
            # Tell the crashMonitor that the temp files have been deleted and it can just exit
            self.pipe.send(('finished', ''))
            self.pipe.close()
