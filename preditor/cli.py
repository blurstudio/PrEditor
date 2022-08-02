from __future__ import absolute_import

import logging
import sys
from distutils.spawn import find_executable

import click
from click_default_group import DefaultGroup

import preditor
from preditor.settings import OS_TYPE

# No one wants to actually type `--help`
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

logger = logging.getLogger(__name__)


@click.group(
    cls=DefaultGroup,
    default='launch',
    default_if_no_args=True,
    context_settings=CONTEXT_SETTINGS,
)
def cli():
    """PrEditor is a Qt based python console and code editor. It runs in many
    DCC's like Maya, Houdini, Nuke, and 3ds Max.

    To see help for launching the PrEditor gui, use `preditor launch -h`.
    """
    pass


@cli.command()
@click.option(
    '-r',
    '--run-workbox',
    is_flag=True,
    help='After the logger is shown, run the current workbox text.',
)
def launch(run_workbox):
    """Run the PrEditor console's gui."""
    preditor.launch(run_workbox=run_workbox, app_id="PrEditor")


@cli.command()
@click.argument("path")
@click.option(
    "-p",
    "--public",
    is_flag=True,
    help='If using "start-menu" or "desktop" for path, create the shortcut '
    'in the public location not the user location. This may require '
    'administrative privileges.',
)
@click.option(
    "--title",
    default="PrEditor",
    help="The shortcut filename.",
)
@click.option(
    "--target",
    default="preditorw",
    help='The command the shortcut will run. "preditor" or "preditorw" are '
    'converted to the full path to the exe.',
)
@click.option(
    '--args',
    default="",
    help="The command the shortcut will run.",
)
@click.option(
    '--description',
    default='Opens PrEditor',
    help="The description to give the shortcut.",
)
@click.option(
    '--app-id',
    default='PrEditor',
    help="On windows set the app id of the shortcut.",
)
def shortcut(path, public, title, target, args, description, app_id):
    """Create a shortcut to launch PrEditor.

    Path is a the full path of the shortcut to create. On windows you can
    pass "start-menu" to create the shortcut in the start menu.
    """

    if OS_TYPE != "Windows":
        click.echo("Creating a shortcut is currently only supported on Windows.")
        sys.exit(1)

    try:
        from casement.shortcut import Shortcut
    except ImportError:
        click.echo(
            "Unable to import casement use `pip install casement` to enable "
            "creating shortcuts on windows."
        )
        sys.exit(1)

    if path in ("desktop", "start-menu"):
        path = [path]

    # Resolve the full path to the preditor exe.
    if target in ("preditor", "preditorw"):
        target = find_executable(target)

    Shortcut.create(
        title,
        args,
        target=target,
        # icon=None,
        icon_source=preditor.resourcePath('img/preditor.ico'),
        icon_filename="preditor",
        path=path,
        description=description,
        common=int(public),
        app_id=app_id,
    )


if __name__ == '__main__':
    cli()
