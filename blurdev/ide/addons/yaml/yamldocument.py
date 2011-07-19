##
# 	\namespace	blurdev.ide.addons.yaml.yamldocument
#
# 	\remarks	Defines the loading/saving/building of Yaml package files
#
# 	\author		eric.hulser@drdstudios.com
# 	\author		Dr. D Studios
# 	\date		05/03/11
#

import re


class YamlDocument(object):
    def __init__(self):
        self._filename = ''
        self._keys = []  # ordered list of keys
        self._data = {}  # dictionary of key/value pairings

    def keys(self):
        return self._keys

    def filename(self):
        return self._filename

    def load(self, filename):
        # load the file
        try:
            f = open(filename, 'r')
            lines = f.readlines()
            f.close()
        except:
            return False

        self._filename = filename

        # create expressions to parse the data
        propexpr = re.compile('^[ \t]*([a-zA-z0-9_-]+)[ \t]*:[ \t]*(.*)$')
        listexpr = re.compile('^-[ \t]*(.*)$')

        currprop = None
        currdata = None
        extends = False

        for line in lines:
            # ignore commented lines
            space_first = line and not line.isspace() and line.startswith(' ')

            # skip blank lines
            if not line or line.isspace():
                continue

            # extract the results
            prop = propexpr.match(line)

            # create new prop
            if prop:
                line = line.strip()
                currprop, currdata = prop.groups()
                extends = currdata.endswith('>')
                self._keys.append(currprop)
                self._data[currprop] = currdata.rstrip('>')
            else:
                listdata = listexpr.match(line)

                # include the listdata
                if listdata:
                    line = line.strip()
                    if currdata and type(currdata) == list:
                        currdata.append(listdata.groups()[0])
                    elif currdata:
                        currdata = [currdata, listdata.groups()[0]]
                        self._data[currprop] = currdata
                    else:
                        currdata = [listdata.groups()[0]]
                        self._data[currprop] = currdata

                # include extensions of a property
                elif extends:
                    line = line.strip()
                    self._data[currprop] += '\n' + line
                    extends = space_first

                # include references to additional lines
                else:
                    self._keys.append(line)

        return True

    def save(self):
        self.saveAs(self._filename)

    def saveAs(self, filename=''):
        if not filename:
            return False

        # record the line data
        lines = []
        first = True

        for prop in self._keys:
            data = self._data.get(prop)

            if data and not first:
                lines.append('')
            else:
                first = False

            # record a list of data
            if type(data) == list:
                lines.append('%s:' % prop)
                lines.append('\n'.join(['- %s' % value for value in data]))

            # record string data
            elif data:
                data_lines = data.split('\n')
                if not data_lines[0]:
                    data_lines[0] = '>'
                for i in range(len(data_lines)):
                    if not data_lines[i]:
                        data_lines[i] = ' >'
                    else:
                        data_lines[i] = ' ' + data_lines[i]

                lines.append('%s: %s' % (prop, data_lines[0]))
                lines += data_lines[1:]

            # record an empty prop
            else:
                lines.append(prop)
                continue

        lines.append('')

        # create the file
        try:
            f = open(filename, 'w')
            f.write('\n'.join(lines))
            f.close()

            self._filename = filename
            return True
        except:
            return False

    def setValue(self, key, value):
        self._data[key] = value
        if not key in self._keys:
            self._keys.append(key)

    def value(self, key, fail=None):
        return self._data.get(key, fail)
