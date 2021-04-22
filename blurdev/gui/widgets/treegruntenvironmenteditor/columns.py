from __future__ import print_function
from __future__ import absolute_import
from blurdev.enum import Enum, EnumGroup


class Column(Enum):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('can_hide', False)
        kwargs.setdefault('visible', True)
        kwargs.setdefault('typ', None)
        super(Column, self).__init__(*args, **kwargs)


class Columns(EnumGroup):
    """Index of the columns the TreegruntEnvironmentEditor displays and their settings"""

    Name = Column(0, 'name')
    Project = Column(1, 'project')
    Path = Column(2, 'path')
    Email = Column(3, 'email', can_hide=True)
    Default = Column(4, 'default', can_hide=True, typ=bool)
    Offline = Column(5, 'offline', can_hide=True, typ=bool)
    Timeout = Column(6, 'timeout', can_hide=True)
    AutoUpdate = Column(7, 'auto_update', can_hide=True, visible=False)
    Keychain = Column(8, 'keychain', can_hide=True, visible=False)
    Legacy = Column(9, 'legacy', can_hide=True, visible=False)
    Dev = Column(10, 'dev', can_hide=True, visible=False, typ=bool)
    Description = Column(11, 'description', can_hide=True)
