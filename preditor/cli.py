import click
import os


@click.command()
@click.option(
    '-r',
    '--run-workbox',
    is_flag=True,
    help='After the logger is shown, run the current workbox text.',
)
def main(run_workbox):
    # When preditor is imported, it will set the ApplicationName to match this.
    os.environ['BDEV_APPLICATION_NAME'] = 'PythonLogger'

    if run_workbox:
        kwargs = {'runWorkbox': True}
    else:
        kwargs = None

    from preditor import setAppUserModelID, launch
    from preditor.gui.loggerwindow import LoggerWindow

    # Set the app user model id here not in the LoggerWindow.__init__ so
    # if a external treegrunt tool calls setAppUserModelID then adds the
    # logger it won't change the id to PythonLogger.
    setAppUserModelID('PythonLogger')
    launch(LoggerWindow.instance, coreName='logger', kwargs=kwargs)


if __name__ == '__main__':
    main()
