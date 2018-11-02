import os
import blurdev
import blurdev.osystem
import subprocess
import configparser
import time
import datetime
from blurdev import version
from blurdev.utils import shortcut

def registryWrapper(root_key, key, value_name, value, valueType, architecture, notify, print_initial_error_msg=True):
    try:
        blurdev.osystem.setRegistryValue(root_key, key, value_name, value, valueType, architecture, notify)
    except TypeError as e:
        if print_initial_error_msg:
            print('Exception, can not update registry key(s):')
        if '' == value_name:
            print('    "%s" with value "%s"' %(key, value))
        else:
            print('    "%s" with value name "%s"' %(key, value_name))
        return False    
    return True

def post_install():
    python_exe = blurdev.osystem.pythonPath(pyw=True, architecture=64)
    module_name = 'blurdev'
    path = os.path.join(os.path.dirname(python_exe), 'Lib', 'site-packages', module_name)

    # Create shortcuts
    shortcut.createShortcutTreegrunt(common=1)
    shortcut.createShortcutBlurIDE(common=1)
 
    # Clear Windows icon cache, continue on fail
    ie4uinit_file_path = r'C:\Windows\system32\ie4uinit.exe'
    proc = subprocess.Popen([ie4uinit_file_path, '-ClearIconCache'], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = proc.wait()
    out = proc.stdout.read().strip()
    if ('' != out) or (0 < proc.returncode):
        print 'Clear of Windows icon cache failed'

    HKCR_root_key = 'HKEY_CLASSES_ROOT'
    HKLM_root_key = 'HKEY_LOCAL_MACHINE'

    key = r'blurdev'
    value_name = ''
    value = 'URL:Blurdev Aplication Protocol'
    valueType = 'REG_SZ'
    architecture = None
    notify = True
    
    ret = registryWrapper(HKCR_root_key, key, value_name, value, valueType, architecture, notify, print_initial_error_msg=True)

    value_name = 'FriendlyTypeName'
    value = 'Blurdev'
    ret = registryWrapper(HKCR_root_key, key, value_name, value, valueType, architecture, notify, True if ret else False)

    value_name = 'URL Protocol'
    value = ''
    ret = registryWrapper(HKCR_root_key, key, value_name, value, valueType, architecture, notify, True if ret else False)

    key = r'blurdev\DefaultIcon'
    value_name = ''
    value = os.path.join(path, 'resource', 'img', 'blurdev.png,1')
    ret = registryWrapper(HKCR_root_key, key, value_name, value, valueType, architecture, notify, True if ret else False)

    key = r'blurdev\shell\open\command'
    value_name = ''
    value = python_exe + ' {} "%1"'.format(os.path.join(path, 'runtimes', 'protocol.pyw'))
    ret = registryWrapper(HKCR_root_key, key, value_name, value, valueType, architecture, notify, True if ret else False)

    key = r'Software\Classes\Python.File\shell\Edit with BlurIDE\command'
    value_name = ''
    value = python_exe + ' ' + os.path.join(path, 'runtimes', 'ide_editor.py') + ' "-f%1"'
    ret = registryWrapper(HKLM_root_key, key, value_name, value, valueType, architecture, notify, True if ret else False)

def update_settings_ini():
    time_in_seconds = time.time()
    st = datetime.datetime.fromtimestamp(time_in_seconds ).strftime('%c')
    config = configparser.ConfigParser()
    config.sections()
    config.read(r'c:\blur\software.ini')

    if not config.has_section('blurdev'):
		# if it does not exist, add blurdev section
        config.add_section('blurdev')
    else:
		# if it exists, the 'blurdev' section
		config.remove_section('blurdev')
    
    day_of_week = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%a')
    month = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%b')
    # while other values are, the day of month is not zero padded in settings.ini
    day_of_month = str(int(datetime.datetime.fromtimestamp(time_in_seconds ).strftime('%d')))
    hour = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%H')
    minute = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%M')
    seconds = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%S')
    year = datetime.datetime.fromtimestamp(time_in_seconds).strftime('%Y')
    
	config.add_section('blurdev')
    config.set('blurdev','installed', '%s %s %s %s:%s:%s %s' %(day_of_week, month, day_of_month, hour, minute, seconds, year))
    config.set('blurdev','version', version.toString(prepend_v=False))

    with open(r'c:\blur\software.ini', 'w') as configfile:
        config.write(configfile)
    
    # Convert Windows newlines to Unix newlines
    windows_line_ending = '\r\n'
    linux_line_ending = '\n'
    filename = r'c:\blur\software.ini'

    with open(filename, 'rb') as f:
        content = f.read()
        content = content.replace(windows_line_ending, linux_line_ending)

    with open(filename, 'wb') as f:
        f.write(content)

def updateEnvirons(verbose=False):
    for env in blurdev.tools.ToolsEnvironment.environments:
        codeRootPath = os.path.abspath(os.path.join(env.path(), 'maxscript', 'treegrunt'))
        if verbose:
            print('Processing:', env.path(), codeRootPath)
        if os.path.exists(codeRootPath):
            blurdev.ini.SetINISetting( blurdev.ini.configFile, env.legacyName(), 'codeRoot', codeRootPath)
            blurdev.ini.SetINISetting( blurdev.ini.configFile, env.legacyName(), 'startupPath', os.path.abspath(os.path.join(codeRootPath, 'lib')))
    # because legacy switching is not enabled by default, update the maxscript environment if it is pointing to the old environments.
    if blurdev.ini.GetINISetting( blurdev.ini.configFile, 'GLOBALS', 'environment') in ('Beta', 'Gold'):
        blurdev.ini.SetINISetting( blurdev.ini.configFile, 'GLOBALS', 'environment', blurdev.tools.ToolsEnvironment.defaultEnvironment().objectName())

if __name__ == '__main__':
    print('Running post-install script')
    post_install()
    print('')
    # print('Updating {}'.format('settings.ini'))
    # update_settings_ini()
    # print('')
    print('Updating {}'.format(blurdev.ini.configFile))
    updateEnvirons()
