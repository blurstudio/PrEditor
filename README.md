# PrEditor

A python Editor and console based on Qt.


# Examples

Common method for adding PrEditor to a Qt widget on startup. This will only create
the PrEditor gui if the user uses the action, but it will be able to show all
`sys.stdout` and `sys.stderr` output written after the `connect_preditor` call.
It will still continue to write to the original stdout/stderr so any existing
output features still work.

```py
# Capture sys.stdout and sys.stderr while still passing the output to
# the original outputs.
# Create your window or dialog
from Qt.QtWidgets import QMainWindow
import preditor

# Create your GUI instance
window = QMainWindow()

# Create a keyboard shortcut to launch preditor and start capturing sys.stdout
# and sys.stderr writes.
action = preditor.connect_preditor(window)
# Add the newly created action to the menu
window.menuBar().addAction(action)
```

Steps for initialization of a more complex application where you don't have
control over the initialization of the Gui(like Maya).

```py
# Step 1: Capture sys.stdout and sys.stderr output to a buffer as early as
# possible without creating the gui. Add this code to a plugin that gets loaded
# as early as possible. This can even be run before the gui is created.
import preditor.stream
preditor.stream.install_to_std()

# Step 2(optional, and rarely needed in host apps): If not already running in
# a QApplication instance, create one.
import preditor.gui.app
preditor.gui.app.App('test')

# Step 3: Add a way for the user to trigger calling this code to actually show
# the PrEditor gui.
import preditor
preditor.show()

# Step 4: When closing the application, calling this will ensure that the
# current PrEditor gui's state is saved. It's safe and fast to call this even
# if the gui was never created.
preditor.shutdown()
```
