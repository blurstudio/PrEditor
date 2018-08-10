import os
import blurdev
import blurdev.osystem
import subprocess
import configparser
import time
import datetime
from blurdev import version


def post_install():
    python_exe = blurdev.osystem.pythonPath(pyw=True)
    here = os.path.abspath(os.path.dirname(__file__))
    module_name = os.path.basename(here)
    print "module_name: %s" % module_name
    if module_name.endswith('_test'):
        module_name = 'blurdev'
    path = os.path.join(
        os.path.dirname(python_exe), 'Lib', 'site-packages', module_name
    )

    # create trax windows desktop shortcut with createShortcut(),
    # which also sets System.AppUserModel.ID, continue on fail
    print "Creating Treegrunt Windows desktop shortcut"
    blurdev.osystem.createShortcut(
        'Treegrunt',
        os.path.join(path, 'runtimes', 'treegrunt.py'),
        path,
        python_exe,
        os.path.join(path, 'resource', 'img', 'treegrunt.ico'),
        None,
        'description',
        1,
    )

    print "Creating Blur IDE Windows desktop shortcut"
    blurdev.osystem.createShortcut(
        'Blur IDE',
        os.path.join(path, 'runtimes', 'ide_editor.py'),
        path,
        python_exe,
        os.path.join(path, 'resource', 'img', 'ide.ico'),
        None,
        'description',
        1,
    )

    # refresh windows icon cache, continue on fail
    print 'Clearing Windows icon cache'
    ie4uinit_file_path = r'C:\Windows\system32\ie4uinit.exe'
    proc = subprocess.Popen(
        [ie4uinit_file_path, '-ClearIconCache'],
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = proc.stdout.read().strip()
    print "output: %s" % output
    print "proc.returncode: %s" % str(proc.returncode)
    if ('' != output) or (0 < proc.returncode):
        print 'Icon cache clear failed'

    HKCR_root_key = 'HKEY_CLASSES_ROOT'
    HKLM_root_key = 'HKEY_LOCAL_MACHINE'

    key = r'blurdev'
    value_name = ''
    value = 'URL:Blurdev Aplication Protocol'
    valueType = 'REG_SZ'
    architecture = None
    notify = True
    blurdev.osystem.setRegistryValue(
        HKCR_root_key, key, value_name, value, valueType, architecture, notify
    )

    value_name = 'FriendlyTypeName'
    value = 'Blurdev'
    blurdev.osystem.setRegistryValue(
        HKCR_root_key, key, value_name, value, valueType, architecture, notify
    )

    value_name = 'URL Protocol'
    value = ''
    blurdev.osystem.setRegistryValue(
        HKCR_root_key, key, value_name, value, valueType, architecture, notify
    )

    key = r'blurdev\DefaultIcon'
    value_name = ''
    value = r'C:\Python27_64\lib\site-packages\blurdev\resource\img\blurdev.png,1'
    blurdev.osystem.setRegistryValue(
        HKCR_root_key, key, value_name, value, valueType, architecture, notify
    )

    key = r'blurdev\shell\open\command'
    value_name = ''
    value = (
        python_exe
        + r' C:\Python27_64\lib\site-packages\blurdev\runtimes\protocol.pyw "%1"'
    )
    blurdev.osystem.setRegistryValue(
        HKCR_root_key, key, value_name, value, valueType, architecture, notify
    )

    key = r'Software\Classes\Python.File\shell\Edit with BlurIDE\command'
    value_name = ''
    value = (
        python_exe + ' ' + os.path.join(path, 'runtimes', 'ide_editor.py') + ' "-f%1"'
    )
    blurdev.osystem.setRegistryValue(
        HKLM_root_key, key, value_name, value, valueType, architecture, notify
    )


def update_settings_ini():
    time_in_seconds = time.time()
    st = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%c')
    config = configparser.ConfigParser()
    config.sections()
    config.read(r'c:\blur\software.ini')

    # if it does not exist, add blurdev section
    if not config.has_section('blurdev'):
        config.add_section('blurdev')

    # if it exists, remove 'filename' option from 'blurdev' section
    if config.has_option('blurdev', 'filename'):
        config.remove_option('blurdev', 'filename')

    day_of_week = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%a')
    month = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%b')
    # while other values are, the day of month is not zero padded in settings.ini
    day_of_month = str(
        int(datetime.datetime.fromtimestamp(time_in_seconds).strftime('%d'))
    )
    hour = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%H')
    minute = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%M')
    seconds = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%S')
    year = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%Y')

    config.set(
        'blurdev',
        'installed',
        '%s %s %s %s:%s:%s %s'
        % (day_of_week, month, day_of_month, hour, minute, seconds, year),
    )
    config.set('blurdev', 'version', version.versionString())

    with open(r'c:\blur\software.ini', 'w') as configfile:
        config.write(configfile)


def updateEnvirons():
    for env in blurdev.tools.ToolsEnvironment.environments:
        codeRootPath = os.path.abspath(
            os.path.join(env.path(), 'maxscript', 'treegrunt')
        )
        print ('Processing:', env.path(), codeRootPath)
        if os.path.exists(codeRootPath):
            blurdev.ini.SetINISetting(
                blurdev.ini.configFile, env.legacyName(), 'codeRoot', codeRootPath
            )
            blurdev.ini.SetINISetting(
                blurdev.ini.configFile,
                env.legacyName(),
                'startupPath',
                os.path.abspath(os.path.join(codeRootPath, 'lib')),
            )
    # because legacy switching is not enabled by default, update the maxscript environment if it is pointing to the old environments.
    if blurdev.ini.GetINISetting(blurdev.ini.configFile, 'GLOBALS', 'environment') in (
        'Beta',
        'Gold',
    ):
        blurdev.ini.SetINISetting(
            blurdev.ini.configFile,
            'GLOBALS',
            'environment',
            blurdev.tools.ToolsEnvironment.defaultEnvironment().objectName(),
        )


if __name__ == '__main__':
    print ('Running post-install script')
    # post_install()
    print ('Updating', 'c:/blurdev/settings.ini')
    update_settings_ini()
    print ('Updating', blurdev.ini.configFile)
    # updateEnvirons()
