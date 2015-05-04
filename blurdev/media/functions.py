import os
import subprocess
import glob
import re
import platform

import blurdev


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


class ColumnLine(list):
    """ Used in conjunction with blurdev.media.columnize for complex column/page generation"""

    def __init__(self, contents, parent=[], blank=False, tags=None):
        super(ColumnLine, self).__init__(contents)
        self.parent = parent
        self.blank = blank
        if tags == None:
            tags = [''] * len(self)
        self.tags = tags


def columnize(data, columns=2, maxLen=60, blank=[]):
    """
    Given a list of ColumnLine's generate pages of columns.
    :param data: List of ColumnLine's
    :param columns: The number of columns to group by
    :param maxLen: The maximum number of rows per page
    :param blank: These blank lines are inserted to make sure all items are returned in the zip process
    
    :returns List of tuples of the source lines
    """
    index = 0
    pages = []
    while index < len(data):
        columnData = []
        rowCount = min(maxLen * columns, len(data) - index + 1)
        # add titles and remove blank lines
        for i in range(columns):
            newIndex = index + (rowCount / columns) * (i + 1)
            isReset = False
            if newIndex >= len(data):
                newIndex = len(data) - 1
                isReset = True
            if data[newIndex].blank:
                data.pop(newIndex)
                isReset = True
                # ensure we have a valid newIndex
                if newIndex >= len(data):
                    newIndex = len(data)
            if not isReset and data[newIndex].parent:
                data.insert(newIndex, data[newIndex].parent)
        rowCount = min(maxLen * columns, len(data) - index + 1)
        if rowCount > 4:
            # build data to be ziped
            for i in range(columns):
                newIndex = index + (rowCount / columns)
                if newIndex >= len(data):
                    newIndex = len(data)
                columnData.append(data[index:newIndex])
                index = newIndex
            rows = len(max(*columnData))
            for i in range(len(columnData)):
                while len(columnData[i]) < rows:
                    columnData[i].append(blank)
            page = zip(*columnData)
        else:
            page = zip(data[index:], (blank * rowCount))
            index = index + rowCount
        pages.append(page)
    return pages


def extractVideoFrame(filename, outputpath):
    """
    This uses ffmpeg to extract a frame as a image.  This requires that 
    ffmpeg is installed by copying the ffmpeg folder into the 32bit 
    program files folder.
    
    """
    options = {}
    options['source'] = filename
    options['ffmpeg'] = r'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
    if not os.path.exists(options['ffmpeg']):
        options['ffmpeg'] = options['ffmpeg'].replace(' (x86)', '')
    options['output'] = outputpath
    cmd = (
        '"\"%(ffmpeg)s\" -i \"%(source)s\" -vframes 1 -f image2 \"%(output)s\""'
        % options
    )
    subprocess.call(cmd, shell=True)
    return os.path.exists(outputpath)


def get32bitProgramFiles():
    if platform.architecture()[0] == '64bit':
        progF = 'ProgramFiles(x86)'
    else:
        progF = 'programfiles'
    return os.getenv(progF)


def html2textile(html, clearStyle=True):
    """ Converts the provided html text to textile markup using html2textile.
    
    Imports the module html2textile and uses it to convert the HTML to textile markup.
    
    Args:
        html (str): The html to convert
        clearStyle (bool): If it should remove style tags first. Use this if you have html
            containing style info that is not respected by this function. QTextEdit generates
            alot of these tags, unfortunately this includes bold.
    
    Raises:
        ImportError: If html2textile is not installed.
    
    Returns:
        str: The textile text.
    """
    import html2textile

    if clearStyle:
        # Remove style tags
        from lxml import etree

        parser = etree.HTMLParser()
        tree = etree.fromstring(html, parser)
        etree.strip_elements(tree, 'style')
        etree.strip_attributes(tree, 'style')
        html = etree.tostring(tree)
    return html2textile.html2textile(html)


def imageMagick(source, destination, exe='convert', flags=''):
    """
    Crafts then runs specified command on ImageMagick executables and waits 
    until it finishes. This assumes Image Magic is installed into 32bit 
    program files. It returns True if the requested exicutable exists path 
    exists.
    
    .. seealso:: 
    
       `ImageMagick <http://www.imagemagick.org/script/index.php>`_
          ImageMagick documentation

    """
    converter = r'%s\ImageMagick\%s.exe' % (get32bitProgramFiles(), exe)
    if os.path.exists(converter):
        cmd = '"%s" %s "%s" "%s"' % (converter, flags, source, destination)
        out = subprocess.Popen(cmd)
        out.wait()
        return True
    return False


def imageSequenceFromFileName(fileName):
    r"""
    Gets a list of files that belong to the same image sequence as the 
    passed in file.
    
        note:: 
    
        This only works if the last number in filename is part of the 
        image sequence.  For example, a file signature like this would 
        not work::

         C:\temp\test_1234_v01.jpg

        It will ignore numbers inside the extension::
    
        C:\temp\test_1234.png1
        
    :rtype: list
    """
    regex = re.compile(r'(?P<pre>^.+?)(?P<frame>\d+)(?P<post>\D*\.[A-Za-z0-9]+?$)')
    fileName = os.path.normpath(fileName)
    match = regex.match(fileName)
    output = []
    if match:
        files = glob.glob('%s*%s' % (match.group('pre'), match.group('post')))
        regex = re.compile(
            r'%s(\d+)%s' % (re.escape(match.group('pre')), match.group('post'))
        )
        for file in files:
            if regex.match(file):
                output.append(file)
    else:
        output = [fileName]
    return output


def imageSequenceRepr(files, strFormat='{pre}[{firstNum}:{lastNum}]{post}'):
    """
    Takes a list of files and creates a string that represents the sequence.
    :param files: A list of files in the image sequence
    :param format: Used to format the output. Uses str.format() command and requires the keys [pre, firstNum, lastNum, post]
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
                    return strFormat.format(
                        pre=match.group('pre'),
                        firstNum=low,
                        lastNum=high,
                        post=match.group('post'),
                    )
    if files:
        return files[0]
    return ''


def imageSequenceReprFromFileName(fileName, strFormat=None):
    """
    Given a filename in a image sequence, return a representation of the image sequence on disk. 
    """
    if strFormat:
        return imageSequenceRepr(
            imageSequenceFromFileName(fileName), strFormat=strFormat
        )
    return imageSequenceRepr(imageSequenceFromFileName(fileName))


def imageSequenceForRepr(fileName):
    """
    Returns the list of file names for a imageSequenceRepr. Only existing 
    files are returned.
    
    :rtype: list
    
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
    Uses PIL to resize the provided image.  *newSize* and *maxSize* expect 
    a 2 position tuple(width, height). If *newSize* is provided, *maxSize* 
    is ignored. *filter* expects a string or Pil.Image 
    filter(BILINEAR, BICUBIC, ANTIALIAS, NEAREST), it will default to BICUBIC.
    
    :param source: the source image to resize, can be a filepath or 
                   :class:`PIL.Image`
    :param newSize: two-item (width, height) tuple
    :param maxSize: two-item (width, height) tuple
    :param filter: a :class:`PIL.Image` filter or the filter name as a string
    :returns: A new, resized :class:`PIL.Image`.  If there is an error during
              the resize, it will return the error id
    :rtype: :class:`PIL.Image` or int

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


def spoolText(**kwargs):
    r"""
    Build a spool string for .msg server parsing. Any passed in keyword 
    arguments are converted to perl dictionary keys::
    
       spoolText(action='symlink', data={'linkname':r'c:\test.txt', 'target':r'c:\test2.test'}, info={'user':'mikeh'}, additonal=5)
       
    """

    def createLink(key, value):
        if isinstance(value, basestring):
            value = "'%s'" % value
        if isinstance(value, dict):
            data = []
            for k, v in value.items():
                data.append(createLink(k, v))
            value = '\n\t{\n\t\t%s\n\t}' % ',\n\t\t'.join(data)
        return '%s => %s' % (key, str(value))

    data = []
    for key, value in kwargs.items():
        data.append(createLink(key, value))
    return '{\n\t%s\n}' % ',\n\t'.join(data)


def setAppIdForIcon(source, new=None):
    r"""
    Uses Win7AppID.exe to add the System.AppUserModel.ID property to 
    windows 7 shortcuts allowing for pinning python applications to taskbars. 
    You need to download the executible from 
    `here <http://code.google.com/p/win7appid/>`_ and place it in 
    *C:\Program Files (x86)\Common Files\Win7AppID\Win7AppId.exe* or 
    equivalent for 32bit apps on your system.
    
    :param source: The icon file to query or modify
    :param new: If None, returns the current appId for source. If a string 
                is provided it will change the appId for source.
                
    :returns: Returns -1 if it can not find the file; otherwise, returns 
              the output of the application as a list.
    :rtype: list or int
    
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
