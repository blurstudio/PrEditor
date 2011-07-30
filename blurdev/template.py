##
# 	\namespace	blurdev.template
#
# 	\remarks	A module of methods for dealing with templating of files and texts
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

import os
import glob

from blurdev import osystem

_templPaths = {
    'default': '$BDEV_PATH/resource/templ/',
}


def allTemplNames():
    names = list(set(templNames() + userTemplNames()))
    names.sort()
    return names


def registerPath(key, path):
    _templPaths[str(key)] = path


def unregisterPath(key):
    if key in _templPaths:
        _templPaths.pop(key)


def templFilename(templname, key='default'):
    import blurdev

    path = _templPaths.get(key)
    if not path and key != 'default':
        return templFilename(templname, key)
    return os.path.join(osystem.expandvars(path), '%s.templ' % templname)


def templ(templname, options={}):
    import blurdev

    # look for the user template
    fname = blurdev.prefPath('templ/%s.templ' % templname)

    keys = _templPaths.keys()
    keys.sort()
    index = 0

    # make sure to use the default templates last
    if 'default' in keys:
        keys.remove('default')
        keys.append('default')

    # look for the installed template
    while fname and not os.path.exists(fname):
        fname = os.path.join(
            osystem.expandvars(_templPaths[keys[index]]), '%s.templ' % templname
        )
        index += 1

    # return the template
    if fname and os.path.exists(fname):
        return fromFile(fname, options)
    return ''


def userTemplFilename(templname):
    import blurdev

    return blurdev.prefPath('templ/%s.templ' % templname)


def userTemplNames():
    import blurdev

    filenames = glob.glob(blurdev.prefPath('templ/*.templ'))

    names = [os.path.basename(filename).split('.')[0] for filename in filenames]
    names.sort()

    return names


def templNames():
    import blurdev

    filenames = []
    for path in _templPaths.values():
        filenames += glob.glob(os.path.join(osystem.expandvars(path), '*.templ'))

    names = [os.path.basename(filename).split('.')[0] for filename in filenames]
    names.sort()

    return names


def fromFile(filename, options={}):
    try:
        f = open(filename, 'r')
        data = f.read()
        f.close()
    except:
        print 'Error opening file', filename
        return ''

    return formatText(data, options)


def formatFile(input, output, options={}):
    try:
        # load the data
        f = open(input, 'r')
        data = f.read()
        f.close()
    except:
        print 'Error opening file from: ', input
        return False

    if data:
        # format the data
        formatted = formatText(data, options)

        # save the data
        f = open(output, 'w')
        f.write(formatted)
        f.close()

        return True
    return False


def formatText(text, options={}):
    text = unicode(text)

    import re

    # replace the document indent with preferenced spacing
    text = text.replace('[  ]', os.environ.get('BDEV_DOCUMENT_INDENT', '    '))

    # process templates
    results = re.findall('\[([a-zA-Z:_-]+)\]', text)

    from PyQt4.QtCore import QDate, QDateTime

    for result in results:
        force = False
        repl = ''
        split = result.split('::')

        # use additional options
        if len(split) == 2:
            check, option = split
        else:
            check = result
            option = ''

        # use standard templates
        if check.startswith('templ'):
            repl = templ(option, options)

        # format date times
        elif check.startswith('datetime'):
            if not option:
                option = 'MM/dd/yy h:mm ap'
            else:
                option = option.replace('_', ' ')

            repl = QDateTime.currentDateTime().toString(option)

        # format dates
        elif check.startswith('date'):
            if not option:
                option = 'MM/dd/yy'
            else:
                option = option.replace('_', ' ')

            repl = QDate.currentDate().toString(option)

        # format author info
        elif check.startswith('author'):
            # include the author's email
            if option == 'email':
                repl = os.environ.get('BDEV_AUTHOR_EMAIL', '')

            if option == 'user':
                repl = os.environ.get('BDEV_AUTHOR_EMAIL', '').split('@')[0]

            # include the author's company
            elif option == 'company':
                repl = os.environ.get('BDEV_AUTHOR_COMPANY', '')

            # include the author's initials
            elif option == 'initials':
                repl = os.environ.get('BDEV_AUTHOR_INITIALS', '')

            # include the author's name
            elif option == 'name':
                repl = os.environ.get('BDEV_AUTHOR_NAME', '')

        # format standard options
        elif check in options:
            repl = options[check]

            # additional formatting options
            if option == 'commented':
                repl = repl.replace('\n', '\n#')

            # escaped option
            elif option == 'escaped':
                repl = repl.replace('\n', '>\n')

            # word option
            elif option == 'words':
                repl = ' '.join(re.findall('[A-Z][^A-Z]+', repl))

            # camelhumps option
            elif option == 'camelhumps':
                repl = ''.join(re.findall('[A-Z][^A-Z]+', repl))

            # lower option
            elif option == 'lower':
                repl = repl.lower()

            # upper option
            elif option == 'upper':
                repl = repl.upper()

            force = True

        if repl or force:
            text = text.replace('[%s]' % result, unicode(repl))

    # replace placeholder []'s
    text = text.replace('\[', '[').replace('\]', ']')

    # process code snippets
    results = re.findall('{!.*(?=!})!}', text)
    for result in results:
        c = result.replace('{!', '').replace('!}', '').strip()
        try:
            ctext = eval(c)
        except:
            ctext = c

        text = text.replace(result, ctext)

    return text
