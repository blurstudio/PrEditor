# 3ds Max Integration

This is an example of using an Autodesk Application Package to load PrEditor into
3ds Max. This adds a PrEditor item to the Scripting menu in 3ds Max's menu bar
to show PrEditor. It adds the excepthook so if a python exception is raised
it will prompt the user to show PrEditor. PrEditor will show all python stdout/stderr
output generated after the plugin is loaded.

# Setup

Make sure to follow these [setup instructions](/preditor/README.md#Setup) first to create the virtualenv.

# Use

The [preditor/dccs/studiomax](/preditor/dccs/studiomax) directory is setup as a 3ds Max Application Plugin.
To load it in 3ds Max add the full path to that directory to the `ADSK_APPLICATION_PLUGINS` environment
variable. You can use `;` on windows and `:` on linux to join multiple paths together.
