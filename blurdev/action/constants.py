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
    Maya = App(label='maya')
    Max = App(label='max')
    XSI = App(label='xsi')
    MotionBuilder = App(label='motionbuilder')
    Fusion = App(label='fusion')
    Nuke = App(label='nuke')
    External = App(label='external')


# =============================================================================
