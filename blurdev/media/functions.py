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

import os, blurdev.osystem


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
    cmd = '"%(ffmpeg)s" -i %(source)s -t 1 -f image2 %(output)s' % options
    print cmd
    os.system(cmd)
    return True


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
