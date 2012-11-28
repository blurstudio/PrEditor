"""
Module for handling user interface preferences

"""

import os
import getpass

from blurdev.XML import XMLDocument
from blurdev import osystem


# cache of all the preferences
_cache = {}


class Preference(XMLDocument):
    """
    A preference document is a sub-class of the XMLDocument and is used for 
    storing custom information about blurdev components, most often tools 
    or views.
    
    """

    def __init__(self):
        XMLDocument.__init__(self)
        self._filename = ''
        self._name = ''
        self._shared = False
        self._coreName = ''

    def coreName(self):
        return self._coreName

    def load(self, filename=''):
        """ loads the preferences from the file, using the current stored filename """
        if not filename:
            filename = self.filename()
        return XMLDocument.load(self, filename)

    def name(self):
        """ return the name attribute """
        return self._name

    def filename(self):
        """ return this documents filename, deriving the default filename from its name and standard preference location  """
        if not self._filename:
            key = self.name().lower().replace(' ', '-')
            self._filename = (
                self.path(coreName=self._coreName, shared=self._shared)
                + '%s.pref' % key
            )
        return self._filename

    def path(self, coreName='', shared=False):
        """ return the path to the application's prefrences folder """
        import blurdev

        # use the core
        if not coreName and blurdev.core:
            coreName = blurdev.core.objectName()
        if shared:
            path = osystem.expandvars(os.environ['BDEV_PATH_PREFS_SHARED']) % {
                'username': getpass.getuser()
            }
        else:
            path = osystem.expandvars(os.environ['BDEV_PATH_PREFS'])
        return os.path.join(path, 'app_%s' % coreName)

    def recordProperty(self, key, value):
        """ connects to the root recordProperty method """
        return self.root().recordProperty(key, value)

    def recordModule(self, module):
        """ record the variables in the inputed module from its dict """
        for key, value in module.__dict__.items():
            # ignore built-ints
            if key.startswith('__'):
                continue
            self.recordProperty(key, value)

    def restoreModule(self, module):
        """ restore proeprties in the module's variables from its dict """
        for key, value in module.__dict__.items():
            # ignore built-ins
            if key.startswith('__'):
                continue
            module.__dict__[key] = self.restoreProperty(key, value)

    def restoreProperty(self, key, default=None):
        """ connects to the root restoreProperty method """
        return self.root().restoreProperty(key, default)

    def save(self, filename=''):
        """ save the preference file """
        if not filename:
            filename = self.filename()
        path = os.path.split(filename)[0]
        # try to create the path
        if not os.path.exists(path):
            os.makedirs(path)
        XMLDocument.save(self, filename)

    def setCoreName(self, coreName):
        self._coreName = coreName

    def setName(self, name):
        """ sets the name of this Preference """
        self._name = name

    def setShared(self, shared):
        self._shared = shared

    def setVersion(self, version):
        """ sets the version number of this preferene """
        self.root().setAttribute('version', version)

    def shared(self, shared):
        return self._shared

    def version(self):
        """ returns the current version of this preference """
        return float(self.root().attribute('version', 1.0))


def clearCache():
    _cache.clear()


def find(name, reload=False, coreName='', shared=False, index=0):
    """
    Finds a preference for the with the inputed name.  If a pref already 
    exists within the cache, then the cached pref is returned; otherwise, 
    it is loaded from the blurdev preference location.

    :param name: the name of the preference to retrieve
    :type name: str
    :param reload: reloads the cached item
    :type reload: bool
    :param coreName: specify a specific core name to save with.
    :type coreName: str
    :param shared: save to the network path not localy. Defaults to False
    :type shared: bool
    :param index: if > 0 append to the end of name. used to make multiple 
                  instances of the same prefs file. If zero it will not 
                  append anything for backwards compatibility. Defaults to 0
    :type index: int
    :rtype: :class:`Preference`

    """
    import blurdev

    key = str(name).replace(' ', '-').lower()
    if index > 0:
        key = '%s%s' % (key, index)
    if reload or not key in _cache:
        # create a new preference record
        pref = Preference()
        pref.setShared(shared)
        pref.setCoreName(coreName)
        # look for a default preference file
        filename = os.path.join(pref.path(coreName, shared), '%s.pref' % key)
        success = False
        if os.path.exists(filename):
            success = pref.load(filename)
        if not success:
            # create default information
            root = pref.addNode('preferences')
            root.setAttribute('name', name)
            root.setAttribute('version', 1.0)
            root.setAttribute('ui', '')
        pref.setName(key)
        _cache[key] = pref
    return _cache[key]
