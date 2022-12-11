# PrEditor

A python REPL and Editor and console based on Qt. It allows you to interact
directly with the current python session and write/run complex code in workbox's.
It also has an interface for configuring python logging.


# Examples

See [examples](examples) for more complete examples of using PrEditor.

For simple standalone applications that only exist for the life of the main window
you can simply call `connect_preditor` in your class `__init__` and optionally add
the created QAction into your GUI's menu. All `sys.stdout` and `sys.stderr` output
written after `connect_preditor` is called, will be shown in the PrEditor window
if it shown. If a exception is raised, and PrEditor is not visible, the user will
be notified and can easily show PrEditor.
```py
import preditor

# Create a keyboard shortcut(F2) to launch PrEditor and start capturing sys.stdout
# and sys.stderr writes. The name argument makes this instance use it for prefs
action = preditor.connect_preditor(window, name="Example")

# Add the newly created action to a menu
window.menuBar().actions()[0].menu.addAction(action)
```

Steps for initialization of a more complex application where you don't have
control over the initialization of the Gui(like Maya).
See [examples/add_to_app.py](examples/add_to_app.py) for a simple implementation.


```py
# Step 1: Capture sys.stdout and sys.stderr output to a buffer as early as
# possible without creating the gui. Add this code to a plugin that gets loaded
# as early as possible. This can even be run before the gui is created.
import preditor
# The name "maya" specifies the core_name that will be used to load/save prefs.
preditor.configure("maya")

# Step 2: Add a way for the user to trigger calling launch to show the PrEditor
# gui. This is the first time the PrEditor GUI is initialized.
preditor.launch()

# Step 3: When closing the application, calling this will ensure that the
# current PrEditor gui's state is saved. It's safe and fast to call this even
# if the gui was never created.
preditor.shutdown()
```

# Installing

`pip install preditor`

## Installing Qt

PrEditor is built on Qt, but uses [Qt.py](https://github.com/mottosso/Qt.py) so
you can choose to use PySide2 or PyQt5. We have elected to not directly depend
on either of these packages as if you want to use PrEditor inside of a an existing
application like Maya or Houdini, they already some with PySide2 installed. If
you are using it externally, add them to your pip install command.

- PySide2: `pip install preditor PySide2`
- PyQt5: `pip install preditor PyQt5`

## Cli

PrEditor is intended to be installed inside existing applications like Maya,
Houdini, Nuke etc, so it doesn't make sense to require installing packages like
click for those installs. If you are setting up a system wide install and want
to use the cli interface, you will need to install the cli optional dependencies.

`pip install preditor[cli]`

### Creating shortcuts

If you want to be able to create desktop shortcuts from the cli to launch
PrEditor, you will also need to include the `shortcut` dependencies. Currently
this is only useful for windows.

- `pip install preditor[cli,shortcut]`

## QScintilla workbox

The more mature QScintilla workbox requires a few extra dependencies that must
be passed manually. It hasn't been added to `extras_require` because we plan to
split it into its own pip module due to it requiring PyQt5 which is a little hard
to get working inside of DCC's that ship with PySide2 by default. Here is the
python 3 pip install command(For python 2 you will need to compile QScintilla
yourself.)

- `pip install preditor PyQt5, QScintilla>=2.11.4 aspell-python-py3`

The aspell-python-py3 requirement is optional to enable spell check.

# Plugins

PrEditor is can be extended using entry point plugins defined by other pip packages.

* `preditor.plug.about_module`: Used to add information about various packages
like version and install location to the output of `preditor.about_preditor()`.
This is what generates the text shown by Help menu -> About PrEditor. See
sub-classes of `AboutModule` in `preditor.about_module` and how those are
added in [setup.cfg](setup.cfg).

* `preditor.plug.editors`: Used to add new workbox editors to PrEditor. See
[workbox_text_edit.py](preditor/gui/workbox_text_edit.py) for an example of
implementing a workbox. See [workbox_mixin.py](preditor/gui/workbox_mixin.py)
for the full interface to implement all features of an editor.

* `preditor.plug.logging_handlers`: Used to add custom python logging handlers
to the LoggingLevelButton's handlers sub-menus. This allows you to install a
handler instance on a specific logging object.
