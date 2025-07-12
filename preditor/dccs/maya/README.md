# Maya Integration

This is an example of using an Maya module to add PrEditor into Maya. This adds
a PrEditor menu with a PrEditor action in Maya's menu bar letting you open PrEditor. It
adds the excepthook so if a python exception is raised it will prompt the user
to show PrEditor. PrEditor will show all python stdout/stderr output generated
after the plugin is loaded.

# Setup

Make sure to follow these [setup instructions](/preditor/README.md#Setup) first to create the virtualenv.

Alternatively you can use [myapy's](https://help.autodesk.com/view/MAYAUL/2026/ENU/?guid=GUID-72A245EC-CDB4-46AB-BEE0-4BBBF9791627) pip to install the requirements, but a
separate virtualenv is recommended. This method should not require setting the
`PREDITOR_SITE` environment variable even if you use an editable install.

# Use

The [preditor/dccs/maya](/preditor/dccs/maya) directory is setup as a Maya Module. To load it in
maya add the full path to that directory to the `MAYA_MODULE_PATH` environment
variable. You can use `;` on windows and `:` on linux to join multiple paths together.
You will need to enable auto load for the `PrEditor_maya.py` plugin.
