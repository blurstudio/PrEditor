# PrEditor

A python REPL, editor and console based on Qt. It allows you to interact
directly with the current python session and write/run complex code in workbox's.
It also has an interface for configuring python logging.

# Use and Features

![preview](https://github.com/blurstudio/PrEditor/assets/2424292/5425aa5f-0f9b-4b04-8e98-5a58546eb93c)

* **Console:** The top section is a python REPL allowing you to run code like you
are in the python interactive shell. However, you can't use code
blocks([...](https://docs.python.org/3/glossary.html#term-...)), use the workbox instead.
    * Python's stdout and stderr are written here including exceptions.
    * If the cursor is at the very end of the last line, and that line starts with
    a prompt (`>>> ` this includes 1 space) the code is executed when you press return.
    Pressing return on any other prompt line copies that line to the end ready to
    execute.
    * Pressing `Ctrl + Up/Down` will cycle through previous command history.
    * The console is a text edit and you can edit any of the text so you can fix
    your mistakes as you make them
* **Workbox:** The workbox is a place to write complex multi-line code. The contents
    of all workboxes are saved when PrEditor is closed or pressing `Ctrl + S`.
    * Workboxes are grouped into tabs of workboxes. You can drag and drop
    individual workboxes between groups and re-order them.
    * `Ctrl + Return` runs all code inside of the current workbox.
    * `Shift + Return` or the `Number-pad Return` executes the selected text or
    the line the cursor is on.
    * `run_workbox("group/tab")` This command is added allowing you to run the
    contents of a workbox. Pass the name of the group and workbox tabs separated
    by a forward slash.
* **Logging Level button:** Tools for managing python loggers.
    * This button shows all known python loggers and lets you view/change their
    logging levels.
    * You can install logging handlers that have had PrEditor plugins written for them.
    * Known python logger levels are saved and restored.
* All code is run in `__main__`. In code you can add objects to it for inspection in PrEditor.
* `Ctrl + Shift + PgUp/PgDown` changes focus between the console and workbox.
* `Ctrl + Alt + Shift + PgUp/PgDown` changes focus and copies the current prompt
line of the console, or the current line of the workbox to the other.


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

Up to the point where the PrEditor instance is created you can update the config
data set by `preditor.configure`. For example you can change the name(used to load
a set of user prefs) by calling `preditor.config.name = 'NewName'`. This is useful
for configuring PrEditor before you import your specific setup code that implements
a better `parent_callback`.

# Installing

`pip install preditor`

## Installing Qt

PrEditor is built on Qt, but uses [Qt.py](https://github.com/mottosso/Qt.py) so
you can choose to use PySide2 or PyQt5. We have elected to not directly depend
on either of these packages as if you want to use PrEditor inside of a an existing
application like Maya or Houdini, they already come with PySide2 installed. If
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
python 3 pip install command.

- `pip install preditor PyQt5, QScintilla>=2.11.4 aspell-python-py3`

The aspell-python-py3 requirement is optional to enable spell check.


# DCC Integration

## Maya

PrEditor is pre-setup to use as a Maya module. To use it, create a virtualenv
with the same python as maya, or install it using mayapy.

```
virtualenv venv_preditor
venv_preditor\Scripts\activate
pip install PrEditor
set MAYA_MODULE_PATH=c:\path\to\venv_preditor\Lib\site-packages\preditor\dccs
```
Note: Due to how maya .mod files works if you are using development installs you
can't use pip editable installs. This is due to the relative path used
`PYTHONPATH +:= ../..` in `PrEditor_maya.mod`. You can modify that to use a hard
coded file path for testing, or add a second .mod file to add the virtualenv's
`site-packages` file path as a hard coded file path.


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

* `preditor.plug.loggerwindow`: Used to customize the LoggerWindow instance when
the LoggerWindow is created. For example, this can be used to create extra Toolbars
or add menu items. When using this plugin, make sure to use the
`preditor.gui.logger_window_plugin.LoggerWindowPlugin` class for your base class.

* `preditor.plug.logging_handlers`: Used to add custom python logging handlers
to the LoggingLevelButton's handlers sub-menus. This allows you to install a
handler instance on a specific logging object.
