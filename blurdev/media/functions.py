from past.builtins import basestring
import errno
import os
import subprocess
import re

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


def convertImageToBase64(image, ext=None):
    """ Convert the given image to a base64 encoded string suitable for web.
    
    Converts the image to base64 encoding and adds the proper header for use in
    a html <img src="data:image/<ext>;base64,<data>"> tag.
    
    You can provide a image filename, or a existing QImage as the first argument.
    If you provide a QImage you must provide the ext.
    
    Args:
        image (str|QImage): A QImage or path to valid file.
        ext (str): The encoding used to convert the image. If image is a file path
            you can use the default of None. If image is a QImage you must provide
            the ext. This is also used to fill out the MIME-type.
    
    Returns:
        str: The image converted to a base64 string.
    
    Raises:
        IOError: The provided file path does not exist.
        ValueError: A QImage was provided but ext was not specified.
    """
    from Qt.QtCore import QBuffer, QByteArray

    if isinstance(image, basestring):
        if not os.path.exists(image):
            raise IOError('Image path does not exist.')
        if not ext:
            ext = os.path.splitext(image)[-1].replace('.', '')
        from Qt.QtGui import QImage

        image = QImage(image)
    else:
        if not ext:
            raise ValueError(
                'When providing a QImage you must provide the image format.'
            )
        # Remove the leading period if provided.
        ext = ext.replace('.', '')
    array = QByteArray()
    buf = QBuffer(array)
    success = image.save(buf, ext)
    if not success:
        raise IOError('{ext} image format is not supported.'.format(ext=ext))
    rawData = array.toBase64().data()
    return 'data:image/{ext};base64,{data}'.format(ext=ext, data=rawData)


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
    if blurdev.osystem.getPointerSize() == 64:
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
    if not html.strip():
        # html2textile errors out if no text or only whitespace is passed to it.
        # So return the unaltered string.
        return html
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


def imageMagickVersion(architecture=64):
    version = None
    try:
        version = blurdev.osystem.registryValue(
            'HKEY_LOCAL_MACHINE',
            r'SOFTWARE\ImageMagick\Current',
            'Version',
            architecture=architecture,
        )
        if '' is version[0]:
            raise WindowsError
        version = version[0]
        version = version.rsplit('.', 1)[0]
        version = float(version)
    except WindowsError as e:
        print("Can not find ImageMagick registry key: {}".format(e))
        raise
    except ValueError as e:
        print("Can not process ImageMagick version: {}".format(e))
        raise
    return version


def imageMagicQuantumDepth(architecture=64):
    quantumDepth = None
    try:
        quantumDepth = blurdev.osystem.registryValue(
            'HKEY_LOCAL_MACHINE',
            r'SOFTWARE\ImageMagick\Current',
            'QuantumDepth',
            architecture=architecture,
        )
        if '' is quantumDepth[0]:
            raise WindowsError
        quantumDepth = quantumDepth[0]
    except WindowsError as e:
        print("Can not find ImageMagick QuantumDepth registry key: {}".format(e))
    return quantumDepth


def imageMagickHDRI(imageMagickEXE):
    HDRI = False
    cmd = [imageMagickEXE, '--version']
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ret = proc.wait()
    out = proc.stdout.readlines()
    for i in out:
        if 'HDRI' in i:
            HDRI = True
    return HDRI


def ensureImageMagickVersion(version=7, architecture=64):
    versionFound = imageMagickVersion(architecture)
    if versionFound < version:
        raise RuntimeError(
            "ImageMagick %s+ required, found %s" % (version, versionFound)
        )


def ensureImageMagickQuantumDepth(quantumDepth=16, architecture=64):
    imageMagickQuantumDepth = imageMagicQuantumDepth(architecture)
    if imageMagickQuantumDepth != quantumDepth:
        raise RuntimeError(
            "ImageMagick quantum depth %s required, %s found"
            % (quantumDepth, imageMagickQuantumDepth)
        )


def ensureImageMagickHDRI(imageMagickEXE, ensureHDRI=True):
    if None is not ensureHDRI:
        HDRI = imageMagickHDRI(imageMagickEXE)
        if HDRI != ensureHDRI:
            if ensureHDRI:
                raise RuntimeError("HDRI version of ImageMagick required")
            else:
                # This branch may not needed
                raise RuntimeError("Non-HDRI version of ImageMagick required")


def getImageMagickEXEHelper(architecture=64):
    # Check/return ImageMagick EXE path
    path = None
    try:
        path = blurdev.osystem.registryValue(
            'HKEY_LOCAL_MACHINE',
            r'SOFTWARE\ImageMagick\Current',
            'BinPath',
            architecture=architecture,
        )
        if '' is path[0]:
            raise WindowsError
        path = os.path.join(path[0], 'magick.exe')
        if not os.path.isfile(path):
            raise OSError(errno.ENOENT, path)
    except WindowsError as e:
        print("Can not find ImageMagick registry key: {}".format(e))
        raise
    return path


def getImageMagickEXE(
    ensureVersion=7, ensureQuantumDepth=16, ensureHDRI=None, architecture=64
):
    imageMagickEXE = getImageMagickEXEHelper(architecture)
    if ensureVersion:
        ensureImageMagickVersion(ensureVersion)
    if ensureQuantumDepth:
        ensureImageMagickQuantumDepth(ensureQuantumDepth)
    if None is not ensureHDRI:
        ensureImageMagickHDRI(imageMagickEXE, ensureHDRI)
    return imageMagickEXE


def imageMagick(
    source,
    destination,
    exe='convert',
    flags='',
    ensureVersion=7,
    ensureQuantumDepth=16,
    ensureHDRI=None,
    architecture=64,
):
    """
    Crafts then runs specified command on ImageMagick executables and waits 
    until it finishes. This assumes Image Magic is installed. It returns True
    if the requested exicutable exists path exists.
    
    .. seealso:: 
    
       `ImageMagick <http://www.imagemagick.org/script/index.php>`_
          ImageMagick documentation

    """
    ret = None
    try:
        converter = getImageMagickEXE(
            ensureVersion=ensureVersion,
            ensureQuantumDepth=ensureQuantumDepth,
            ensureHDRI=ensureHDRI,
            architecture=architecture,
        )
        if converter:
            if flags:
                cmd = [converter, exe, flags, source, destination]
            else:
                cmd = [converter, exe, source, destination]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            ret = proc.wait()
    except (OSError, RuntimeError, ValueError, WindowsError) as e:
        return False
    return True if 0 == ret else False


def escapeForGlob(text):
    """ Glob treats [] as escapes or number ranges, replaces these with escape characters. 
    
    http://stackoverflow.com/a/2595162 We have to escape any additional [ or ] or glob 
    will not find any matches.
    
    Args:
        text (str): The text to escape
    
    Returns:
        str: The output text
    """

    def replaceText(match):
        return '[{}]'.format(match.group(0))

    checks = [
        '(?<!\[)\[(?![\]\[])',  # [ but not [[]
        '(?<![\]\[])\](?!\])',  # ] but not []]
    ]
    return re.sub('|'.join(checks), replaceText, text)


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
    flags = 0
    if blurdev.settings.OS_TYPE == 'Windows':
        flags = re.I
    match = imageSequenceInfo(fileName)
    output = []
    if match:
        import glob

        path = '%s*%s' % (match.group('pre'), match.group('post'))
        files = glob.glob(escapeForGlob(path))
        regex = re.compile(
            r'%s(\d+)%s' % (re.escape(match.group('pre')), match.group('post')),
            flags=flags,
        )
        for file in files:
            if regex.match(file):
                output.append(file)
    if not output:
        output = [os.path.normpath(fileName)]
    return output


def imageSequenceInfo(path, osystem=None):
    """ Return a re.match object that seperates the file path into pre/postfix and frame number.
    
    Args:
        path (str): The path to split
        osystem (str): pass 'Windows' to make the check case insensitive. If None(the default) is
            passed in it will default to the contents of blurdev.settings.OS_TYPE.
    
    Returns:
        match: Returns the results of the re.match call or None
    """
    flags = 0
    if osystem == None:
        osystem = blurdev.settings.OS_TYPE
    if osystem == 'Windows':
        flags = re.I
    # Look for ScXXX or SXXXX.XX to include in the prefix. This prevents problems with incorrectly
    # identifying a shot number as a image sequence. Thanks willc.

    # match seq/shot format used by studio

    seqShotPattern = r'(?:Sc\d{3}|S\d{4}\.\d{2})?\D*?(?:_v\d+\D*)?'
    # grab all digits for the frame number
    framePattern = r'(?P<frame>\d+)?'
    # match anything after our frame (that isn't a digit), and include a file extension
    # Frame number will be expected to be the LAST digits that appear before the extension because
    # of this.
    postPattern = r'(?P<post>\.[A-Za-z0-9]+?$)'
    # Assemble the pieces of our pattern into the full match pattern for filenames
    filePattern = r'(?P<pre>^.+?' + seqShotPattern + r')' + framePattern + postPattern
    regex = re.compile(filePattern, flags=flags)
    path = os.path.normpath(path)
    m = regex.match(path)
    if m and m.group('frame'):
        return m
    else:
        # If we don't have a match object or a match for the frame group, we want to return None
        # (we don't want to conisder it an imageSequence.)
        # We could do this in our regular expression, but it would require more complicated logic,
        # so I think this is easier to read.
        return None


def imageSequenceRepr(
    files, strFormat='{pre}[{firstNum}:{lastNum}]{post}', forceRepr=False
):
    """ Takes a list of files and creates a string that represents the sequence.
    Args:
        files (list): A list of files in the image sequence.
        strFormat (str): Used to format the output. Uses str.format() command and requires the 
            keys [pre, firstNum, lastNum, post]. Defaults to '{pre}[{firstNum}:{lastNum}]{post}'
        forceRepr (bool): If False and a single frame is provided, it will return just that frame.
            If True and a single frame is provided, it will return a repr with that frame as the
            firstNum and lastNum value. False by default.
    
    Returns:
        str: A string representation of the Image Sequence.
    """
    if len(files) > 1 or (forceRepr and files):
        match = imageSequenceInfo(files[0])
        if match:
            info = {}
            for f in files:
                frame = imageSequenceInfo(f)
                if frame and frame.group('frame'):
                    frame = frame.group('frame')
                    info.update({int(frame): frame})
            if info:
                keys = sorted(info.keys())
                low = info[keys[0]]
                high = info[keys[-1]]
                if forceRepr or low != high:
                    return strFormat.format(
                        pre=match.group('pre'),
                        firstNum=low,
                        lastNum=high,
                        post=match.group('post'),
                    )
    if files:
        return files[0]
    return ''


def imageSequenceReprFromFileName(fileName, strFormat=None, forceRepr=False):
    """
    Given a filename in a image sequence, return a representation of the image sequence on disk. 
    """
    if strFormat:
        return imageSequenceRepr(
            imageSequenceFromFileName(fileName),
            strFormat=strFormat,
            forceRepr=forceRepr,
        )
    return imageSequenceRepr(imageSequenceFromFileName(fileName), forceRepr=forceRepr)


def imageSequenceForRepr(fileName):
    """
    Returns the list of file names for a imageSequenceRepr. Only existing 
    files are returned.
    
    :rtype: list
    
    """
    flags = 0
    if blurdev.settings.OS_TYPE == 'Windows':
        flags = re.I
    filter = re.compile(
        r'(?P<pre>^.+?)\[(?P<start>\d+)(?P<separator>[^\da-zA-Z]?)(?P<end>\d+)\](?P<post>\.[A-Za-z0-9]+?$)',
        flags=flags,
    )
    match = re.match(filter, fileName)
    if match:
        import glob

        start = int(match.group('start'))
        end = int(match.group('end'))
        path = '%s*%s' % (match.group('pre'), match.group('post'))
        files = glob.glob(escapeForGlob(path))
        pre = re.escape(match.group('pre'))
        regex = re.compile(
            r'%s(?P<frame>\d+)%s' % (pre, match.group('post')), flags=flags
        )
        # Filter the results of the glob and return them in the image sequence order
        out = {}
        for f in files:
            match = regex.match(f)
            if match and start <= int(match.group('frame')) <= end:
                out.update({int(match.group('frame')): f})
        # Return the file paths sorted by frame number
        return [out[key] for key in sorted(out)]
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
    
       spoolText(action='symlink', data={'linkname':r'c:\test.txt', 'target':r'c:\test2.test'}, info={'user':'mikeh'}, additional=5)
       
    """

    def toPerlString(value):
        if isinstance(value, basestring):
            return "'%s'" % (value.replace("'", r"\'"))
        return str(value)

    def createLink(key, value):
        if isinstance(value, basestring):
            value = toPerlString(value)
        if isinstance(value, (list, tuple)):
            value = [toPerlString(v) for v in value]
            value = '[\n\t\t\t%s\n\t\t]' % ',\n\t\t\t'.join(value)
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


def spoolFileName(prefix, host='thor', folders=['new'], uid=''):
    """ Generate a unique filename for a spool message on the given host.
    
    Builds a full path for a .msg file. It uses uuid.uuid4 to ensure
    a unique file name. 
    
    Example output: 
        \\thor\spool\new\magma7a934858-a6d9-42bc-b57e-15c8e95258d1.msg
    
    Args:
        prefix (str): Prefix of the uuid for the msg file.
        host (str): The name of the smb share host. Defaults to 'thor'.
        folders (list): List of folders to put after '\\[host]\spool' using
            os.path.join(). Defaults to ['new'].
        uid (str): The unique part of the string. If nothing is provided
            uses uuid.uuid4() to generate a unique id.
    
    Returns:
        str: The generated filename.
    """
    if not uid:
        import uuid

        uid = uuid.uuid4()
    args = [r'\\{}'.format(host), 'spool']
    args.extend(folders)
    args.append('{0}{1}.msg'.format(prefix, uid))
    filename = os.path.abspath(os.path.join(*args))
    return filename


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
        out = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out.wait()
        return out.stdout.readlines()
    return -1


def naturalSort(l):
    """ taken from: http://blog.codinghorror.com/sorting-for-humans-natural-sort-order/ """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def sizeof_fmt(num, suffix='B', iec=False):
    """ Convert the given number of bytes into the nicest MB, GB, etc value.
    
    Original source: http://stackoverflow.com/a/1094933 Author: Sridhar Ratnakumar
    
    Args:
        num (int|long): The byte value you want to convert to a nice name.
        suffix (str): The suffix you would like to add to the end. Defaults to 'B'.
        iec (bool): The size label will follow "IEC prefixes". Defaults to False.
            See "https://en.wikipedia.org/wiki/Binary_prefix#Adoption_by_IEC.2C_NIST_and_ISO"
    
    Returns:
        str: A string with num converted to a nice format. For example "16.0 MB".
    """
    iec = 'i' if iec else ''
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s%s" % (num, unit, iec, suffix)
        num /= 1024.0
    return "%.1f %s%s%s" % (num, 'Y', iec, suffix)
