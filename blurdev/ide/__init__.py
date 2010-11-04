##
# 	\namespace	blurdev.ide
#
# 	\remarks	The blurdev IDE allows you to quickly and easily create and edit python files
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

from ideeditor import IdeEditor

from ideproject import IdeProject


def createFromTemplate(filename, templateName, outputFilename, options):
    templ = template(filename, templateName)
    f = open(outputFilename, 'w')
    f.write(templ % options)
    f.close()
    return True


def remarks(text):
    remarks = []
    first = True
    for line in str(text).split('\n'):
        if not first:
            remarks.append('#\t\t%s' % line)
        else:
            remarks.append(line)

    return '\n'.join(remarks)


def template(filename, templateName):
    import os.path

    templpath = os.path.split(filename)[0] + '/tmpl/%s' % templateName
    if os.path.exists(templpath):
        f = open(templpath, 'r')
        data = f.read()
        f.close()
        return data
    return ''
