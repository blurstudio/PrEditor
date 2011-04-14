##
# 	\namespace	blurdev.ide.main.py
#
# 	\remarks	Runs the IdeEditor as an application
#
# 	\author		beta@blur.com
# 	\author		Blur Studio
# 	\date		08/19/10
#

# if this is run directly
if __name__ == '__main__':
    import blurdev
    import sys
    from blurdev.ide.ideeditor import IdeEditor

    # launch the editor
    argv = sys.argv
    if len(argv) > 1:
        blurdev.launch(IdeEditor.instance, coreName='ide', filename=argv[1])
    else:
        editor = blurdev.launch(IdeEditor.instance, coreName='ide')
