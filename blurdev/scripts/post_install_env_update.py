import blurdev, os


def updateEnvirons():
    for env in blurdev.tools.ToolsEnvironment.environments:
        codeRootPath = os.path.abspath(
            os.path.join(env.path(), 'maxscript', 'treegrunt')
        )
        print 'Processing:', env.path(), codeRootPath
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


if __name__ == '__main__':
    print 'Updating', blurdev.ini.configFile
    updateEnvirons()
