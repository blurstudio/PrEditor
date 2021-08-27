##
# 	\namespace	blurdev.zipper
#
# 	\remarks	methods for archiving and unarchiving files
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		03/21/11
#
from __future__ import absolute_import


def packageFiles(files, outputfile):
    """Packages the inputed files to the output file location

    Args:
        files (list): [ <str> filename, .. ]
        outputfile (str):

    Returns:
        bool: success
    """
    if not files:
        return False

    import random
    import os
    import shutil

    temppath = 'c:/temp/archive%i' % int(random.random() * 1000000)

    # create the temp path
    if not os.path.exists(temppath):
        os.makedirs(temppath)

    # copy the files to the temp path
    for filename in files:
        shutil.copyfile(filename, '%s/%s' % (temppath, os.path.basename(filename)))

    # call the package path function
    success = packagePath(temppath, outputfile)

    # remove the temp path
    shutil.rmtree(temppath)

    return success


def packagePath(path, outputfile):
    """Packages all the information at the inputed path to the output file location

    Args:
        path (str):
        outputfile (str):

    Returns:
        bool: success
    """
    from blurdev import debug
    import os
    from Qt.QtCore import QProcess

    # TODO: Remove this module. The code calling it should be using the zipfile module.
    zipexe = os.get('BDEV_APP_ZIP')
    if not zipexe:
        return False

    # create the zip command
    zipcmd = r'%s -j %s %s\*' % (
        os.path.normpath(zipexe),
        os.path.normpath(outputfile),
        os.path.normpath(path),
    )

    # determine based on debugging level if we should let this process with or without a
    # try/catch
    if debug.isDebugLevel(debug.DebugLevel.Mid):
        debug.debugObject(packagePath, 'Running zip command: %s' % (zipcmd))
        failure = QProcess.execute(zipcmd)

    else:
        try:
            failure = QProcess.execute(zipcmd)
        except Exception:
            debug.debugObject(
                packagePath,
                'Could not package %i files to %s path (%s zip EXE)'
                % (path, outputfile, zipexe),
            )
            failure = 1

    return not failure
