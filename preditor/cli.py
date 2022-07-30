import click
import os

from casement.app_id import AppId


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

    from preditor import launch
    from preditor.gui.loggerwindow import LoggerWindow

    # Set the app user model id here not in the window class so it doesn't
    # try to set the app id for applications that already set the app id.
    AppId.set_for_application("Preditor")
    launch(LoggerWindow.instance, coreName='logger', kwargs=kwargs)


if __name__ == '__main__':
    main()
