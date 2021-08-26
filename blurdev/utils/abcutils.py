"""
Utilities and tools for reading and writing alembic files.

"""

from __future__ import print_function
from __future__ import absolute_import
import re
import os
import logging

# set the exocortex license server env var
os.environ["EXOCORTEX_LICENSE"] = "5053@mandarin004"
import _ExocortexAlembicPython as Alembic


def copyArchive(src, dst):
    archive = ABCArchive.fromFile(src)
    archive.toFile(dst)
    del archive


def printArchive(src):
    archive = ABCArchive.fromFile(src)
    print(archive.toString())
    del archive


def readArchive(src):
    return ABCArchive.fromFile(src)


def getIdentifiers(filepath):
    iarchive = Alembic.getIArchive(filepath)
    return iarchive.getIdentifiers()


def getPolyMeshObjectNames(iarchive):
    re_poly = re.compile(r"^/(?P<name>[^/]+)Xfo$")
    poly_names = []
    for id in iarchive.getIdentifiers():
        m = re_poly.match(id)
        if m:
            poly_names.append(m.group('name'))
    return poly_names


class ABCArchive(object):

    indent = "  "

    def __init__(self):
        super(ABCArchive, self).__init__()
        self.filename = None
        self.version = None
        self.sampletimes = None
        self.objects = None

    def toString(self, indent=""):
        txt = []
        txt.append('ARCHIVE: %s' % self.filename)
        obj_names = sorted(self.objects.keys())
        indent += ABCArchive.indent
        for obj_name in obj_names:
            obj = self.objects[obj_name]
            txt.append(obj.toString(indent))
        return '\n'.join(txt)

    def getIdentifiers(self):
        return self.objects.keys()

    def getPolyMeshObjectNames(self):
        re_poly = re.compile(r"^/(?P<name>[^/]+)Xfo$")
        poly_names = []
        for id in self.getIdentifiers():
            m = re_poly.match(id)
            if m:
                poly_names.append(m.group('name'))
        return poly_names

    @classmethod
    def from_iArchive(cls, iarchive):
        archive = cls()
        archive.filename = iarchive.getFileName()
        archive.version = iarchive.getVersion()
        archive.sampletimes = iarchive.getSampleTimes()
        archive.objects = {}
        for oid in iarchive.getIdentifiers():
            iobj = iarchive.getObject(oid)
            archive.objects[oid] = ABCObject.from_iObject(iobj, archive)
        return archive

    @classmethod
    def fromFile(cls, filename):
        logging.debug("Reading file: %s" % filename)
        iarchive = Alembic.getIArchive(filename)
        archive = ABCArchive()
        archive.filename = iarchive.getFileName()
        archive.version = iarchive.getVersion()
        archive.sampletimes = iarchive.getSampleTimes()
        archive.objects = {}
        logging.debug("Reading iArchive objects...")
        for oid in iarchive.getIdentifiers():
            iobj = iarchive.getObject(oid)
            archive.objects[oid] = ABCObject.from_iObject(iobj)
        iarchive = None
        return archive

    def toFile(self, filename):
        logging.debug("Writing oArchive to file: %s" % filename)
        oarchive = Alembic.getOArchive(filename)
        if self.sampletimes:
            # TODO: not sure what the 2d array is?
            oarchive.createTimeSampling(self.sampletimes[1])

        def _copy_property(prop, oprop):
            for i in range(0, prop.nbstoredsamples):
                vals = prop.values[i]
                oprop.setValues(vals)

        def _copy_compound_property(prop, oprop):
            for sub_prop in prop.properties.values():
                if sub_prop.compound:
                    _copy_compound_property(
                        sub_prop, oprop.getProperty(sub_prop.name, sub_prop.type)
                    )
                else:
                    _copy_property(
                        sub_prop, oprop.getProperty(sub_prop.name, sub_prop.type)
                    )

        oids = self.objects.keys()
        oids.sort()
        for oid in oids:
            obj = self.objects[oid]
            oobj = oarchive.createObject(obj.type, obj.id)
            if obj.metadata:
                # TODO: might need to pad metadata
                oobj.setMetaData(obj.metadata)
            if obj.properties:
                for prop in obj.properties.values():
                    oprop = oobj.getProperty(prop.name, prop.type)
                    if prop.compound:
                        _copy_compound_property(prop, oprop)
                    else:
                        _copy_property(prop, oprop)
        oarchive = None


class ABCObject(object):
    def __init__(self):
        super(ABCObject, self).__init__()
        self.id = None
        self.metadata = None
        self.type = None
        self.sampletimes = None
        self.nbstoredsamples = None
        self.properties = None
        self.abcarchive = None

    def toString(self, indent=""):
        txt = []
        txt.append('%s%s (%s)' % (indent, self.id, self.type))
        txt.append('%s--metadata: %s' % (indent, str(self.metadata)))
        indent += ABCArchive.indent
        propnames = sorted(self.properties.keys())
        for propname in propnames:
            prop = self.properties[propname]
            txt.append(prop.toString(indent))
        return '\n'.join(txt)

    @classmethod
    def from_iObject(cls, iobj, abcarchive=None):
        logging.debug("  Reading iObject: %s..." % iobj.getIdentifier())
        obj = cls()
        obj.abcarchive = abcarchive
        obj.id = iobj.getIdentifier()
        obj.metadata = iobj.getMetaData()
        obj.type = iobj.getType()
        obj.sampletimes = iobj.getSampleTimes()
        obj.nbstoredsamples = iobj.getNbStoredSamples()
        obj.properties = {}
        for pid in iobj.getPropertyNames():
            iprop = iobj.getProperty(pid)
            obj.properties[pid] = ABCProperty.from_iProperty(iprop, obj)
        return obj


class ABCProperty(object):
    def __init__(self):
        super(ABCProperty, self).__init__()
        self.name = None
        self.type = None
        self.sampletimes = None
        self.nbstoredsamples = None
        self.size = None
        self.values = None
        self.abcobject = None
        self.abcarchive = None
        self.compound = None
        self.properties = None

    def toString(self, indent=""):
        txt = []
        txt.append('%s%s (%s)' % (indent, self.name, self.type))
        if self.compound:
            indent += ABCArchive.indent
            propnames = sorted(self.properties.keys())
            for propname in propnames:
                prop = self.properties[propname]
                txt.append(prop.toString(indent))
        else:
            txt.append('%s--size: %s' % (indent, str(self.size)))
            for i in range(self.nbstoredsamples):
                valtxt = '%s--values(%s): %s' % (indent, i, self.values[i])
                txt.append(valtxt)
        return '\n'.join(txt)

    @classmethod
    def from_iProperty(cls, iprop, abcobject=None, abcproperty=None):
        logging.debug("    Reading iProperty: %s..." % iprop.getName())
        prop = cls()
        prop.abcobject = abcobject
        if abcobject is not None:
            prop.abcarchive = abcobject.abcarchive
        logging.debug("      Reading Name and Type...")
        prop.name = iprop.getName()
        prop.type = iprop.getType()
        logging.debug("      Reading SampleTimes...")
        prop.sampletimes = iprop.getSampleTimes()
        logging.debug("      Reading NbStoredSamples...")
        prop.nbstoredsamples = iprop.getNbStoredSamples()
        logging.debug("      Reading Size...")
        prop.size = iprop.getSize()
        prop.values = []
        logging.debug("      Reading Values...")
        for i in range(prop.nbstoredsamples):
            vals = iprop.getValues(i)
            prop.values.append(vals)

        prop.compound = iprop.isCompound()
        if prop.compound:
            logging.debug("      Reading SubProperties...")
            prop.properties = {}
            for sub_iprop_name in iprop.getPropertyNames():
                sub_iprop = iprop.getProperty(sub_iprop_name)
                sub_prop = ABCProperty.from_iProperty(sub_iprop, abcobject, prop)
                prop.properties[sub_iprop_name] = sub_prop
        return prop
