"""Utilities and tools for reading fume caches.

"""

import sys
import struct

from blurdev.enum import enum


def readFXD(filename):
    """
    Convenience function for returning a :class:`FXDFile` object 
    representing the given filename.
    
    """
    return FXDFile.read(filename)


class FXDFile(object):
    """
    Reader for fxd fume caches.  Currently, it only supports reading the
    fxd headers.
    
    Information about the header is stored in the "attributes" attribute
    dictionary.
    
    """

    ChannelTypes = enum(
        "None", "Fuel", "Temp", "Smoke", "Fluid", "Velocity", "Voxel", "Color"
    )
    """Enumerated type for the types of channels a fume cache may contain."""

    def __init__(self):
        super(FXDFile, self).__init__()
        self.filename = ''
        self.attributes = {}

    @classmethod
    def read(cls, filename):
        """
        Reads the fume cache at the given filepath and returns a
        :class:`FXDFile` instance representing that cache.
        
        """
        fxd = FXDFile()
        fxd.filename = filename

        sizeof_ushort = 2
        sizeof_int = 4
        sizeof_float = 4
        sizeof_bool = 1

        fmt_ushort = 'H'
        fmt_int = 'i'
        fmt_float = 'f'
        fmt_bool = '?'

        f = open(filename, 'rb')
        (outputFileVer,) = struct.unpack(fmt_ushort, f.read(sizeof_ushort))
        (step,) = struct.unpack(fmt_int, f.read(sizeof_int))
        (fileScale,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (dx,) = struct.unpack(fmt_float, f.read(sizeof_float))

        (lx,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (ly,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (lz,) = struct.unpack(fmt_float, f.read(sizeof_float))

        (lxmax,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (lymax,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (lzmax,) = struct.unpack(fmt_float, f.read(sizeof_float))

        (nx,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (ny,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (nz,) = struct.unpack(fmt_float, f.read(sizeof_float))

        (nx0,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (ny0,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (nz0,) = struct.unpack(fmt_float, f.read(sizeof_float))

        (nxmax,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (nymax,) = struct.unpack(fmt_float, f.read(sizeof_float))
        (nzmax,) = struct.unpack(fmt_float, f.read(sizeof_float))

        # struct boolean reading isn't supported in 2.4 (is in 2.6)
        # 	adaptive, = struct.unpack(fmt_bool, f.read(sizeof_bool))
        adaptive = bool(ord(f.read(sizeof_bool)))

        (outputvars,) = struct.unpack(fmt_int, f.read(sizeof_int))
        outvars = [
            cls.ChannelTypes.toString(v)
            for v in cls.ChannelTypes.values()
            if int(str(outputvars)) & v
        ]

        f.close()

        attributes = fxd.attributes
        attributes['outputFileVer'] = outputFileVer
        attributes['step'] = step
        attributes['fileScale'] = fileScale
        attributes['dx'] = dx
        attributes['lx'] = lx
        attributes['ly'] = ly
        attributes['lz'] = lz
        attributes['lxmax'] = lxmax
        attributes['lymax'] = lymax
        attributes['lzmax'] = lzmax
        attributes['nx'] = nx
        attributes['ny'] = ny
        attributes['nz'] = nz
        attributes['nx0'] = nx0
        attributes['ny0'] = ny0
        attributes['nz0'] = nz0
        attributes['nxmax'] = nxmax
        attributes['nymax'] = nymax
        attributes['nzmax'] = nzmax
        attributes['adaptive'] = adaptive
        attributes['outputvars'] = outputvars
        attributes['channelTypes'] = outvars

        return fxd
