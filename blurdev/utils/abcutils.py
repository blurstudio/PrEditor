import sys
import os
from pprint import pprint

# set the exocortex license server env var
os.environ["EXOCORTEX_LICENSE"] = "5053@mandarin004"
import _ExocortexAlembicPython as alembic


def copyarchive(src, dst):
    archive = ABCArchive.fromfile(src)
    archive.tofile(dst)
    del archive


def printarchive(src):
    archive = ABCArchive.fromfile(src)
    print archive.tostring()
    del archive


class ABCArchive(object):
    def __init__(self):
        super(ABCArchive, self).__init__()
        self.filename = None
        self.version = None
        self.sampletimes = None
        self.objects = None

    def tostring(self):
        txt = []
        txt.append('ARCHIVE: %s' % self.filename)
        obj_names = sorted(self.objects.keys())
        for obj_name in obj_names:
            obj = self.objects[obj_name]
            txt.append(obj.tostring())
        return '\n'.join(txt)

    @classmethod
    def from_iArchive(cls, iarchive):
        archive = cls()
        archive.filename = iarchive.getFileName()
        archive.version = iarchive.getVersion()
        archive.sampletimes = iarchive.getSampleTimes()
        archive.objects = {}
        for oid in iarchive.getIdentifiers():
            iobj = iarchive.getObject(oid)
            archive.objects[oid] = ABCObject.from_iObject(iobj)
        return archive

    @classmethod
    def fromfile(cls, filename):
        iarchive = alembic.iArchive(filename)
        archive = ABCArchive()
        archive.filename = iarchive.getFileName()
        archive.version = iarchive.getVersion()
        archive.sampletimes = iarchive.getSampleTimes()
        archive.objects = {}
        for oid in iarchive.getIdentifiers():
            iobj = iarchive.getObject(oid)
            archive.objects[oid] = ABCObject.from_iObject(iobj)
        iarchive = None
        return archive

    def tofile(self, filename):
        oarchive = alembic.oArchive(filename)
        errors = []
        try:
            if self.sampletimes:
                # TODO: not sure what the 2d array is?
                oarchive.createTimeSampling(self.sampletimes[1])

            oids = self.objects.keys()
            oids.sort()
            for oid in oids:
                obj = self.objects[oid]
                try:
                    oobj = oarchive.createObject(obj.type, obj.id)
                except alembic.error:
                    errors.append('OBJECT: %s, %s' % (obj.type, obj.id))
                else:
                    if obj.metadata:
                        # TODO: might need to pad metadata
                        oobj.setMetaData(obj.metadata)
                    if obj.properties:
                        for prop in obj.properties.values():
                            try:
                                oprop = oobj.getProperty(prop.name, prop.type)
                            except alembic.error:
                                errors.append(
                                    'OBJECT: %s, %s ||| PROP: %s, %s'
                                    % (obj.type, obj.id, prop.type, prop.name)
                                )
                            else:
                                oprop.setValues(prop.values)
        finally:
            oarchive = None
        print 'ERRORS'
        pprint(errors)


class ABCObject(object):
    def __init__(self):
        super(ABCObject, self).__init__()
        self.id = None
        self.metadata = None
        self.type = None
        self.sampletimes = None
        self.nbstoredsamples = None
        self.properties = None

    def tostring(self):
        txt = []
        txt.append('    %s (%s)' % (self.id, self.type))
        propnames = sorted(self.properties.keys())
        for propname in propnames:
            prop = self.properties[propname]
            txt.append(prop.tostring())
        return '\n'.join(txt)

    @classmethod
    def from_iObject(cls, iobj):
        obj = cls()
        obj.id = iobj.getIdentifier()
        obj.metadata = iobj.getMetaData()
        obj.type = iobj.getType()
        obj.sampletimes = iobj.getSampleTimes()
        obj.nbstoredsamples = iobj.getNbStoredSamples()
        obj.properties = {}
        for pid in iobj.getPropertyNames():
            iprop = iobj.getProperty(pid)
            obj.properties[pid] = ABCProperty.from_iProperty(iprop)
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

    def tostring(self):
        txt = []
        txt.append('        %s (%s)' % (self.name, self.type))
        return '\n'.join(txt)

    @classmethod
    def from_iProperty(cls, iprop):
        prop = cls()
        prop.name = iprop.getName()
        prop.type = iprop.getType()
        prop.sampletimes = iprop.getSampleTimes()
        prop.nbstoredsamples = iprop.getNbStoredSamples()
        prop.size = iprop.getSize()
        prop.values = iprop.getValues()
        return prop


def main():
    fp = sys.argv[1]
    archive = ABCArchive.fromfile(fp)
    print '\n\n'
    print archive.tostring()


if __name__ == '__main__':
    main()
