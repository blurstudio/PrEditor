##
# 	\namespace	python.apps.trax.api.media
#
# 	\remarks	The media package contains modules for managing external meida applications for trax usage
#
# 	\author		eric@blur.com
# 	\author		Blur Studio
# 	\date		01/11/11
#

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

# -------------------------------------------


def extractVideoFrame(filename, outputpath):
    import trax

    options = {}
    options['source'] = filename
    options['ffmpeg'] = trax.api.formatPath('[trax]/resource/ffmpeg.exe')
    options['output'] = outputpath

    cmd = '%(ffmpeg)s -i %(source)s -t 1 -f image2 %(output)s' % options

    import os

    os.system(cmd)
    return True


def isMovie(filename):
    import os.path

    ext = os.path.splitext(str(filename))[0]

    # return if the extension type is in the movies dictionary
    return ext in _movieFileTypes
