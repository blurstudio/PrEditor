# 3ds Max Integration

This is an example of using an Autodesk Application Package to load PrEditor into
3ds Max. This adds a PrEditor item to the Scripting menu in 3ds Max's menu bar
to show PrEditor. It adds the excepthook so if a python exception is raised
it will prompt the user to show PrEditor. PrEditor will show all python stdout/stderr
output generated after the plugin is loaded.

# Setup

PrEditor has many python pip requirements. The easiest way to get access to all
of them is to create a virtualenv and pip install the requirements. You can possibly use the python included with 3ds Max, but this guide covers using a system install of python.

1. Identify the minor version of python that 3ds Max is using. 3ds Max 2025 and 2026 are both using python 3.11. The version of python is printed when you first activate python mode in the Scripting Listener.
2. Download and install the required version of python. Note, you likely only need to match the major and minor version of python(3.11 not 3.11.12). It's recommended that you don't use the windows store to do this as it has had issues when used to create virtualenvs.
3. Create a virtualenv using that version of python. On windows you can use `py.exe -3.11` or call the correct python.exe file.
    ```batch
    cd c:\path\to\venv\parent
    py -3.11 -m virtualenv preditor_venv
    ```
4. Use the newly created pip exe to install PrEditor and its dependencies.
    * This example shows using PySide and the simple TextEdit workbox in a minimal configuration.
        ```batch
        c:\path\to\venv\parent\preditor_venv\Scripts\pip install PrEditor
        ```
    * This example shows using QScintilla in PyQt6 for a better editing experience. Note that you need to match the Qt version used by 3ds Max. Both 2025 and 2026 use 6.5.3.
        ```batch
        c:\path\to\venv\parent\preditor_venv\Scripts\pip install PrEditor[qsci6] PyQt6==6.5.3
        ```

# Use

There are a few environment variables that need to be set. They can be set permanently, but this
example shows setting them temporarily for the current command prompt window.
Note that these paths are referencing the site-packages folder of the virtualenv.

1. Open a command prompt.
2. Set the `ADSK_APPLICATION_PLUGINS` variable. This env var is used by 3ds Max to load the package defined by the PackageContents.xml file. If you are using an editable install of PrEditor, this should point to it's `preditor\dccs\studiomax` folder not inside the virtualenv's site-packages.
    ```batch
    set "ADSK_APPLICATION_PLUGINS=c:\path\to\venv\parent\preditor_venv\Lib\site-packages\preditor\dccs\studiomax"
    ```
3. Set the `PREDITOR_SITE` variable. This env var is used to make the packages in the virtualenv's site-packages accessible in 3ds Max's python. The virtualenv is only used to handle the pip installations, 3ds Max doesn't activate the virtualenv, it just makes its site-packages folder importable.
    ```batch
    set "PREDITOR_SITE=c:\path\to\venv\parent\preditor_venv\Lib\site-packages"
    ```
4. Optional: If using QScintilla, you will also need to force Qt.py to load it instead of PySide by setting `QT_PREFERRED_BINDING` or `QT_PREFERRED_BINDING_JSON`.
    ```batch
    set "QT_PREFERRED_BINDING=PyQt6"
    ```
5. Launch 3ds Max.
    ```batch
    "C:\Program Files\Autodesk\3ds Max 2026\3dsmax.exe"
    ```
