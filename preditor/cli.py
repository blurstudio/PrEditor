from __future__ import absolute_import

import logging
import sys
from distutils.spawn import find_executable

import click
from click.core import ParameterSource
from click_default_group import DefaultGroup

import preditor
import preditor.prefs
from preditor.settings import OS_TYPE

# No one wants to actually type `--help`
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

logger = logging.getLogger(__name__)


def get_app_id(name, is_default):
    """Returns the name to use for the app_id of windows shortcuts.
    This allows for taskbar/start menu pinning.
    """
    if is_default:
        # If not using a custom name, just use it for the app_id
        return name
    # Otherwise use a prefix of the name provided by the user
    return "PrEditor - {}".format(name)


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


# launch
@cli.command()
@click.option(
    "-n",
    "--name",
    default=preditor.DEFAULT_CORE_NAME,
    envvar="PREDITOR_NAME",
    help="Name to save preferences with. This allows you to open multiple "
    "instances with their own code and settings.",
)
@click.option(
    '-r',
    '--run-workbox',
    is_flag=True,
    help='After the logger is shown, run the current workbox text.',
)
def launch(name, run_workbox):
    """Run the PrEditor console's gui."""
    # Check if the user passed the name or it was the default
    parameter_source = click.get_current_context().get_parameter_source('name')
    app_id = get_app_id(name, parameter_source == ParameterSource.DEFAULT)

    preditor.launch(run_workbox=run_workbox, app_id=app_id, name=name)


# shortcut
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
    "-n",
    "--name",
    default=preditor.DEFAULT_CORE_NAME,
    envvar="PREDITOR_NAME",
    help="Name to save preferences with. This allows you to open multiple "
    "instances with their own code and settings.",
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
def shortcut(path, public, name, target, args, description):
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

    parameter_source = click.get_current_context().get_parameter_source('name')
    if parameter_source == ParameterSource.DEFAULT:
        app_id = name
    else:
        # Strip off the leading "launch " command argument if it was passed
        if args.startswith('launch '):
            args = args[7:]
        # Pass the name to the launched PrEditor instance
        args = 'launch --name "{}" {}'.format(name, args)
        app_id = name = get_app_id(name, parameter_source == ParameterSource.DEFAULT)

    Shortcut.create(
        name,
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


# prefs
@cli.group()
def prefs():
    """PrEditor preference management."""
    pass


@prefs.command()
def backup():
    """Backup all of preferences inside a zip file."""
    zip_path = preditor.prefs.backup()
    click.echo('PrEditor Preferences backed up to "{}"'.format(zip_path))


@prefs.command()
@click.argument("name", default="", required=False)
def browse(name):
    """Open a file explorer to the preference directory. Optionally pass the
    name of a specific preference.
    """
    preditor.prefs.browse(name)


@prefs.command()
def list():
    """List the core_names for existing preferences."""
    click.echo("Existing pref names:")
    click.echo("--------------------")
    for pref in preditor.prefs.existing():
        click.echo(pref)


if __name__ == '__main__':
    cli()
