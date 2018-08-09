##
# 	\namespace	build
#
# 	\remarks	Sets up the build system for the package installers
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		06/11/10
#

if __name__ == '__main__':
    import sys

    print(sys.version)

    # --------------------------------------------------------------------------------
    # Setup the correct build environment to allow importing of Qt.py
    import blurpath

    # Setup the PATH env variable, sys.path and QT_PREFERRED_BINDING to the correct values
    blurpath.installPathsForSoftware('python', '')
    # --------------------------------------------------------------------------------

    from blur.build import *
    import blur.build
    import sys, os
    from blurdev import template

    product = sys.argv[1]

    # make sure the path exists for the package
    path = os.path.dirname(os.path.abspath(__file__))
    dirpath = os.path.abspath(path + '/..')
    if not dirpath in sys.path:
        sys.path.append(dirpath)

    from optparse import OptionParser

    # Temporary until a blur-utils package is made
    sys.path.insert(0, r'\\source\production\code\python\lib')
    import blurutils.version

    version = blurutils.version.Version(path)

    blur.build.Parser = 1

    # determine what python folder to install to
    parser = OptionParser()
    parser.add_option('-v', '--version', dest='version', default='Python27')
    parser.add_option('-i', '--install', dest='install', default='0')
    parser.add_option('-s', '--silent', dest='silent', default='0')
    parser.add_option('-o', '--offline', dest='offline', default='0')
    parser.add_option('-n', '--nsiLibs', dest='nsiLibs', default=r'..\..\..\nsis')
    parser.add_option('-c', '--copy', dest='copyTo', default='')

    (options, args) = parser.parse_args()
    dictionary = options.__dict__

    # create the global defines from input
    f = open(path + '/installers/autogen.nsi', 'w')
    f.write('!define MUI_PRODUCT "%s"\n' % product)
    f.write(
        '!define MUI_VERSION "v%i.%02i.%i"\n'
        % (version.major(), version.minor(), version.currentBuild())
    )
    f.write('!define INSTALL_VERSION "v%i.%02i"\n' % (version.major(), version.minor()))
    f.write('!define PYTHON_VERSION "%s"\n' % dictionary['version'])
    f.write('!define OFFLINE %s\n' % dictionary['offline'])
    f.write("!define NSI_LIBS '%s'\n" % dictionary['nsiLibs'])

    if dictionary['offline'] == '1':
        f.write(
            '!define OUTPUT_FILENAME "bin\offline\${MUI_PRODUCT}-install-${INSTALL_VERSION}.${MUI_SVNREV}-offline.exe"\n'
        )
        # When Building a offline build of blurdev, update the dummy records that are used to ensure trax gui dummy widgets work.
        import trax

        if trax.isValid:
            print('**************************************************')
            print('*             Exporting trax data                *')
            print('**************************************************')
            import blurdev.traxoffline.trax

            blurdev.traxoffline.trax.api.data.createRoleList(
                r'%s\traxoffline\trax\api\data\source\roles.xml' % path
            )
            blurdev.traxoffline.trax.api.data.createApprovalType(
                r'%s\traxoffline\trax\api\data\source\approvalTypes.xml' % path
            )
            blurdev.traxoffline.trax.api.data.createDepartmentList(
                r'%s\traxoffline\trax\api\data\source\departments.xml' % path
            )
        # Create a offline copy of settings.ini and update any paths that may not exist offline
        print('**************************************************')
        print('*            Updating settings.ini               *')
        print('**************************************************')
        srcPath = r'%s\resource\settings.ini' % path
        destPath = r'%s\installers\resource\settings.ini' % path
        import shutil

        shutil.copyfile(srcPath, destPath)
        import blurdev.ini

        blurdev.ini.SetINISetting(
            destPath,
            'Windows',
            'BDEV_PATH_PREFS_SHARED',
            '$BDEV_PATH_PREFS',
            useConfigParser=True,
        )
        blurdev.ini.SetINISetting(
            destPath,
            'Windows',
            'BDEV_ENVIRONMENT_OVERRIDE_FILEPATH',
            '',
            useConfigParser=True,
        )
        blurdev.ini.SetINISetting(
            destPath, 'Windows', 'BDEV_ADMIN_USERNAMES', '', useConfigParser=True
        )
        blurdev.ini.SetINISetting(
            destPath,
            'Windows',
            'BDEV_DISABLE_TOOL_USAGE_LOG',
            'True',
            useConfigParser=True,
        )
        blurdev.ini.SetINISetting(
            destPath,
            'Windows',
            'BDEV_PATH_ICONS',
            r'C:\blur\icons',
            useConfigParser=True,
        )
        blurdev.ini.SetINISetting(
            destPath,
            'Windows',
            'BDEV_SPLASHSCREEN_SOURCE_DIR',
            r'C:\blur\splash',
            useConfigParser=True,
        )
        # 		blurdev.ini.SetINISetting(destPath, 'Windows', 'BDEV_TRAX_ON_DCC_STARTUP', r'false', useConfigParser=True)
        # remove non blur specific includes in tools_environments.xml
        print('**************************************************')
        print('*          Updating tools environments           *')
        print('**************************************************')
        doc = blurdev.XML.XMLDocument()
        envXML = os.path.join(path, 'resource', 'tools_environments.xml')
        destXML = os.path.join(path, 'installers', 'resource', 'tools_environments.xml')
        doc.load(envXML)
        root = doc.root()
        for child in root.children():
            if child.name().lower() == 'include':
                aPath = os.path.abspath(child.attribute('loc'))
                if aPath.startswith(r'\\source'):
                    print('  Removing network path', child.name(), aPath)
                    child.remove()
            if child.name().lower() == 'environment':
                print(
                    '  Removing existing environment.',
                    child.name(),
                    child.attribute('loc'),
                )
                child.remove()
        # Add the offline environment
        # <environment	name="Blur Offline" loc="c:/blur/dev/offline" default="True" legacyName="Offline" offline="True"/>
        print('  Adding the offline environment')
        child = root.addNode('environment')
        child.setAttribute('name', 'Blur Offline')
        child.setAttribute('loc', 'c:/blur/dev/offline')
        child.setAttribute('default', 'True')
        child.setAttribute('offline', 'True')
        child.setAttribute('legacyName', 'Offline')
        doc.save(destXML)

    else:
        f.write(
            '!define OUTPUT_FILENAME "bin\${MUI_PRODUCT}-install-${INSTALL_VERSION}.${MUI_SVNREV}.exe"\n'
        )

    f.close()

    svnnsi = WCRevTarget(
        'svnrevnsi',
        path,
        path,
        'installers/svnrev-template.nsi',
        'installers/svnrev.nsi',
    )
    svnpy = WCRevTarget(
        'svnrevpy', path, path, 'installers/version-template.txt', 'build.txt'
    )
    nsi = NSISTarget('installer', path, 'installers/installer.nsi')

    Target(product, path, [svnnsi, svnpy], [nsi])

    global Parser
    Parser = parser
    build()

    # see if the user wants to run the installer
    f = open(path + '/installers/svnrev.nsi', 'r')
    lines = f.read()
    f.close()

    import re

    results = re.search('!define MUI_SVNREV "(\d+)"', lines)

    if results:

        if dictionary['offline'] == '1':
            outFile = '%s-install-v%i.%02i.%s-offline.exe' % (
                product,
                version.major(),
                version.minor(),
                results.groups()[0],
            )
            filename = path + '/installers/bin/offline/' + outFile
        else:
            outFile = '%s-install-v%i.%02i.%s.exe' % (
                product,
                version.major(),
                version.minor(),
                results.groups()[0],
            )
            filename = path + '/installers/bin/' + outFile
    if dictionary['install'] == '1':
        import os

        if dictionary['silent'] == '1':
            # Silent install
            print('Silently installing: ', filename)
            os.system('%s /S' % filename)
        else:
            os.startfile(filename)
    paths = dictionary['copyTo']
    if paths:
        import shutil

        for output in paths.split('|'):
            copyTo = template.formatText(output, {'filename': outFile})
            print('*** Copying file to "%s"' % copyTo)
            shutil.copyfile(filename, copyTo)
