##
# 	\namespace	python.apps.trax.api.media
#
# 	\remarks	The media package contains modules for managing external media
# 				applications for trax usage.
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		01/11/11
#

import os
import subprocess
import glob
import re
import platform

import blurdev.osystem
import blurdev.settings
import blurdev.debug


_movieFileTypes = {
    '.mov': ('Quicktime Files', 'QuickTime'),
    '.mp4': ('MPEG 4', 'VLC Player'),
    '.avi': ('Avi Files', 'VLC Player'),
}

_imageFileTypes = {
    '.jpg': ('JPEG Files', ''),
    '.png': ('PNG Files', ''),
    '.exr': ('EXR Files', ''),
    '.tga': ('Targa Files', ''),
}


def extractVideoFrame(filename, outputpath):
    """
        \Remarks	This uses ffmpeg to extract a frame as a image.
                    This requires that ffmpeg is installed by copying the ffmpeg folder into the 32bit program files folder
    """
    options = {}
    options['source'] = filename
    options['ffmpeg'] = blurdev.osystem.programFilesPath(r'ffmpeg\bin\ffmpeg.exe')
    options['output'] = outputpath
    cmd = '"%(ffmpeg)s" -i "%(source)s" -t 1 -f image2 "%(output)s"' % options
    print cmd
    out = subprocess.Popen(cmd)
    out.wait()
    # 	os.system(cmd)
    return os.path.exists(outputpath)


def get32bitProgramFiles():
    if platform.architecture()[0] == '64bit':
        progF = 'ProgramFiles(x86)'
    else:
        progF = 'programfiles'
    return os.getenv(progF)


def imageMagick(source, destination, exe='convert', flags=''):
    """
        \Remarks	Crafts then runs specified command on ImageMagick executables and waits until it finishes. This assumes Image Magic is 
                    installed into 32bit program files. It returns True if the requested exicutable exists path exists.
        \param		source		<str>
        \param		destination	<str>
        \param		exe			<str>
        \param		flags		<str>
        \sa			http://www.imagemagick.org/script/index.php
        \Return		<bool>
    """
    converter = r'%s\ImageMagick\%s.exe' % (get32bitProgramFiles(), exe)
    if os.path.exists(converter):
        cmd = '"%s" %s "%s" "%s"' % (converter, flags, source, destination)
        out = subprocess.Popen(cmd)
        out.wait()
        return True
    return False


def imageSequenceFromFileName(fileName):
    """
        \Remarks	Gets a list of files that belong to the same image sequence as the passed in file.
        \Note		This only works if the last number in filename is part of the image sequence.
                    "c:\temp\test_[frame]_v01.jpg" A file signature like this would not work.
                    It will ignore numbers inside the extension. Example("C:\temp\test_[frame].png1")
        \Return		<list>
    """
    regex = re.compile(r'(?P<pre>^.+?)(?P<frame>\d+)(?P<post>\D*\.[A-Za-z0-9]+?$)')
    fileName = os.path.normpath(fileName)
    match = regex.match(fileName)
    output = []
    if match:
        files = glob.glob('%s*%s' % (match.group('pre'), match.group('post')))
        regex = re.compile(
            r'%s(\d+)%s'
            % (match.group('pre').replace('\\', '\\\\'), match.group('post'))
        )
        for file in files:
            if regex.match(file):
                output.append(file)
    else:
        output = [fileName]
    return output


def imageSequenceRepr(files):
    """
        \Remarks	Takes a list of files and creates a string that represents the sequence
        \Return		<str>
    """
    if len(files) > 1:
        regex = re.compile(r'(?P<pre>^.+?)(?P<frame>\d+)(?P<post>\D*\.[A-Za-z0-9]+?$)')
        match = regex.match(files[0])
        if match:
            info = {}
            for file in files:
                frame = regex.match(file)
                if frame:
                    frame = frame.group('frame')
                    info.update({int(frame): frame})
            if info:
                keys = sorted(info.keys())
                low = info[keys[0]]
                high = info[keys[-1]]
                if low != high:
                    return '%s[%s:%s]%s' % (
                        match.group('pre'),
                        low,
                        high,
                        match.group('post'),
                    )
    if files:
        return files[0]
    return ''


def imageSequenceForRepr(fileName):
    """
        \Remarks	Returns the list of file names for a imageSequenceRepr. Only existing files are returned.
        \Return		<list>
    """
    fileName = unicode(fileName)
    filter = re.compile(
        r'(?P<pre>^.+?)\[(?P<start>\d+):(?P<end>\d+)\](?P<post>\.[A-Za-z0-9]+?$)'
    )
    match = re.match(filter, fileName)
    if match:
        start = int(match.group('start'))
        end = int(match.group('end'))
        files = glob.glob('%s*%s' % (match.group('pre'), match.group('post')))
        regex = re.compile(
            r'%s(?P<frame>\d+)%s'
            % (match.group('pre').replace('\\', '\\\\'), match.group('post'))
        )
        out = []
        for file in files:
            match = regex.match(file)
            if match and start <= int(match.group('frame')) <= end:
                out.append(file)
        return out
    return [fileName]


def isMovie(filename):
    ext = os.path.splitext(str(filename))[0]
    return ext in _movieFileTypes


def isImageSequence(filename):
    ext = os.path.splitext(str(filename))[0]
    return ext in _imageFileTypes and '#' in filename


def isImage(filename):
    ext = os.path.splitext(str(filename))[0]
    return ext in _imageFileTypes


def imageFileTypes():
    return ';;'.join(
        ['All File Types (*.*)']
        + ['%s (*%s)' % (value[0], key) for key, value in _imageFileTypes.items()]
    )


def movieFileTypes():
    return ';;'.join(
        ['All File Types (*.*)']
        + ['%s (*%s)' % (value[0], key) for key, value in _movieFileTypes.items()]
    )


def fileTypes():
    return ';;'.join(
        ['All File Types (*.*)']
        + [
            '%s (*%s)' % (value[0], key)
            for key, value in _imageFileTypes.items() + _movieFileTypes.items()
        ]
    )


def openQuicktime(filename):
    if blurdev.settings.OS_TYPE == 'Windows':
        import _winreg

        # look up quicktime's path using the registry and the com id
        areg = _winreg.ConnectRegistry(None, _winreg.HKEY_CLASSES_ROOT)
        akey = _winreg.OpenKey(areg, r'QuickTimePlayerLib.QuickTimePlayerApp\CLSID')
        clsid = _winreg.QueryValueEx(akey, '')[0]
        envKey = _winreg.OpenKey(areg, r'Wow6432Node\CLSID\%s\LocalServer32' % clsid)
        path = _winreg.QueryValueEx(envKey, '')[0]
        cmd = '%s "%s"' % (path, os.path.normpath(filename))
        subprocess.Popen(cmd)


def resizeImage(source, newSize=None, maxSize=None, filter=None):
    """
        \Remarks	Uses PIL to resize the provided image. newSize and maxSize expect a 2 position tuple(width, height). If newSize is provided, 
                    maxSize is ignored. filter expects a string or Pil.Image filter(BILINEAR, BICUBIC, ANTIALIAS, NEAREST), it will default to BICUBIC.
        \param		source		<str>||<unicode>||<PIL.Image>
        \param		newSize		<tuple>||None
        \param		maxSize		<tuple>||None
        \param		filter		<str>||<unicode>||<Pil.Image.BILINEAR>||<Pil.Image.BICUBIC>||<Pil.Image.ANTIALIAS>||<Pil.Image.NEAREST>
        \Return		<Pil.Image>||<int>		If successfull returns the resized Pil.Image. If it failed it will return a tuple containing error id, and a error message.
    """
    try:
        from PIL import Image
    except ImportError:
        return -1, 'Unable to import PIL'
    if filter == None:
        filter = Image.BICUBIC
    elif isinstance(filter, (str, unicode)):
        try:
            filter = getattr(Image, filter)
        except AttributeError:
            return -2, 'Invalid resize filter specified.'
    if isinstance(source, (str, unicode)):
        try:
            source = Image.open(source)
        except IOError:
            return -3, 'Unable to open the specified image'
    if newSize:
        return source.resize(newSize, filter)
    if maxSize:
        width, height = source.size
        if not width or not height:
            return -4, 'The selected image has a invalid width or height.'
        if width > maxSize[0] or height > maxSize[1]:
            if width > height:
                height = int(round((float(maxSize[0]) / width) * height))
                width = maxSize[0]
            else:
                width = int(round((float(maxSize[1]) / height) * width))
                height = maxSize[1]
            return source.resize((width, height), filter)
    return source


def spoolText(action, data, user=None):
    # replace removes the extra tabs required to make it look nice in source code
    source = """{
        action => %(action)s,
        data =>
        {
            %(data)s
        }
        %(extra)s
    }""".replace(
        '\n\t', '\n'
    )

    def createLink(key, value):
        if isinstance(value, basestring):
            value = "'%s'" % value
        return '%s => %s' % (key, str(value))

    dataInfo = []
    for key in data:
        dataInfo.append(createLink(key, data[key]))
    extra = []
    if user:
        extra.append("info => { user => '%s' }" % user)
    return source % {
        'action': action,
        'data': '\n\t\t'.join(dataInfo),
        'extra': '\n\t'.join(extra),
    }


def setAppIdForIcon(source, new=None):
    """
        \Remarks	Uses Win7AppID.exe to add the System.AppUserModel.ID property to windows 7 shortcuts allowing for pinning python applications 
                    to taskbars. You need to download the executible from http://code.google.com/p/win7appid/ and place it in 
                    C:\Program Files (x86)\Common Files\Win7AppID\Win7AppId.exe or equivalent for 32bit apps on your system.
        \param		source	<str>			The icon file to query or modify
        \param		new		<str>||None		If None, returns the current appId for source. If a string is provided it will change the appId for source.
        \return		<list>||<int>			Returns -1 if it can not find the file, other wise returns the output of the application as a list.
    """
    appId = r'%s\Common Files\Win7AppId\Win7AppId.exe' % get32bitProgramFiles()
    if os.path.exists(appId):
        cmd = '"%s" "%s"' % (appId, source)
        if new:
            cmd += ' %s' % new
        print cmd
        out = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out.wait()
        return out.stdout.readlines()
    return -1
