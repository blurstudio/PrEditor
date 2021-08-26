from __future__ import absolute_import
import blurdev
import click


@click.group()
def cli():
    """ Create Shortcut. """
    pass


@cli.command()
@click.option(
    '-t',
    '--target',
    default=None,
    help="Set the target path for this shortcut.",
)
@click.option(
    '-p',
    '--path',
    default=None,
    help="Set the destination path of this shortcut."
)
@click.argument(
    'title',
    default=None,
    # TODO: This can be optional when we extend this cli to create the shortcuts
    # defined in blurdev.utils.shortcuts and add support for creating treegrunt
    # shortcuts as well as pkg_resources shortcut definitions.
    # required=False,
)
def create(title, target, path):
    """ Creates a Shortcut. Title is the name of the created shortcut.
    """

    msg = ['Created {title} shortcut']

    if target:
        msg.append('for: {target}')
    if path:
        msg.append('in: {path}')

    blurdev.osystem.createShortcut(title, '', target=target, path=path, app_id=False)

    click.echo(' '.join(msg).format(title=title, target=target, path=path))
