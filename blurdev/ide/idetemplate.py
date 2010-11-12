##
# 	\namespace	blurdev.ide.pluginbuilder.plugins
#
# 	\remarks	These plugins allow you to quickly and easily create components of a tool or class
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#


class IdeTemplate:
    def __init__(self):
        self.name = ''

        self.templateId = ''

        self.language = ''
        self.group = ''
        self.desc = ''
        self.toolTip = ''
        self.iconFile = ''
        self.module = ''
        self.cls = ''

    def runWizard(self):
        import sys

        __import__(self.module)

        module = sys.modules[self.module]
        cls = module.__dict__.get(self.cls)
        return cls.runWizard()

    @staticmethod
    def formatFile(input, output, options):

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

            formatted = IdeTemplate.formatText(data, options)

            # save the data

            f = open(output, 'w')

            f.write(formatted)

            f.close()

            return True

        return False

    @staticmethod
    def formatText(text, options):

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

            # format date times

            if check.startswith('datetime'):

                if not option:

                    option = 'MM/dd/yy h:mm ap'

                repl = QDateTime.currentDateTime().toString(option)

            # format dates

            elif check.startswith('date'):

                if not option:

                    option = 'MM/dd/yy'

                repl = QDate.currentDate().toString(option)

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

    @staticmethod
    def fromXml(filename):
        from blurdev.XML import XMLDocument

        doc = XMLDocument()
        import os.path

        output = []
        if doc.load(filename):
            root = doc.root()

            for xml in root.children():
                templ = IdeTemplate()

                templ.language = xml.attribute('language', 'Python')
                templ.name = xml.attribute('name', 'New Template')
                templ.group = xml.attribute('group', 'Default')

                templ.templateId = '%s::%s::%s' % (
                    templ.language,
                    templ.group,
                    templ.name,
                )
                templ.toolTip = '<b>%s</b><br><small>%s</small>' % (
                    templ.name,
                    xml.findProperty('toolTip'),
                )
                templ.desc = xml.findProperty('desc')
                templ.iconFile = os.path.join(
                    os.path.split(filename)[0], xml.findProperty('icon')
                )
                templ.module = xml.findProperty('module')
                templ.cls = xml.findProperty('class')
                output.append(templ)
        return output
