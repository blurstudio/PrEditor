##
# 	\namespace	blurdev.template
#
# 	\remarks	A module of methods for dealing with templating of files and texts
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#


def templ(templname, options={}):

    import os.path, blurdev

    fname = blurdev.resourcePath('templ/%s.templ' % templname)

    if os.path.exists(fname):

        return fromFile(fname, options)

    return ''


def templNames():

    import glob, os.path, blurdev

    filenames = glob.glob(blurdev.resourcePath('templ/*.templ'))

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

    text = str(text)

    import re

    results = re.findall('\[([^\]]+)\]', text)

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

            result = templ(option)

            if result:

                repl = result

        # format date times

        elif check.startswith('datetime'):

            if not option:

                option = 'MM/dd/yy h:mm ap'

            repl = QDateTime.currentDateTime().toString(option)

        # format dates

        elif check.startswith('date'):

            if not option:

                option = 'MM/dd/yy'

            repl = QDate.currentDate().toString(option)

        # format author info

        elif check.startswith('author'):

            # include the author's email

            if option == 'email':

                repl = 'beta@blur.com'

            # include the author's company

            if option == 'company':

                repl = 'Blur Studio'

            # include the author's initials

            if option == 'initials':

                repl = 'EKH'

        # format standard options

        elif check in options:

            repl = options[check]

            # additional formatting options

            if option == 'commented':

                repl = '\n#'.join(repl.split('\n'))

            # word option

            if option == 'words':

                repl = ' '.join(re.findall('[A-Z][^A-Z]+', repl))

            # lower option

            if option == 'lower':

                repl = repl.lower()

            # upper option

            if option == 'upper':

                repl = repl.upper()

            force = True

        if repl or force:

            text = text.replace('[%s]' % result, str(repl))

    return text
