from blurdev.enum import Enum, EnumGroup

# =============================================================================
# ENUMS
# =============================================================================


class App(Enum):
    """An enum representation of an application context.
    """

    pass


# =============================================================================


class Apps(EnumGroup):
    Maya = App(label='maya', traxName='Maya')
    Max = App(label='max', traxName='3ds Max')
    XSI = App(label='xsi', traxName='XSI')
    MotionBuilder = App(label='motionbuilder', traxName='MotionBuilder')
    Fusion = App(label='fusion', traxName='Fusion')
    Nuke = App(label='nuke', traxName='Nuke')
    Houdini = App(label='houdini', traxName='Houdini')
    External = App(label='external', traxName='')


# =============================================================================
