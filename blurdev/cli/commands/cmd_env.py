import blurdev
import click
from tabulate import tabulate


@click.group()
def cli():
    """ Manage treegrunt environments. """
    pass


@cli.command()
@click.option(
    '-n', '--name', help="Use this treegrunt environment instead of the active one."
)
def rebuild(name):
    """ Rebuild this treegrunt environment's index """

    active = blurdev.activeEnvironment()
    if name is None:
        name = active.objectName()
    if active.findEnvironment(name).isEmpty():
        raise ValueError('The environment "{}" is not valid.'.format(name))

    # Cache current environment
    curenv = blurdev.activeEnvironment().objectName()
    # Get the backup environment so that the index can be rebuilt
    blurdev.setActiveEnvironment(name)
    click.echo(' Rebuilding Environment: {} '.format(name).center(80, '-'))

    blurdev.activeEnvironment().index().rebuild()
    # Reset original environment
    blurdev.setActiveEnvironment(curenv)
    click.echo('Finished')


@cli.command('list')
def list_environments():
    """ Show info about treegrunt environments """

    if list:
        rows = []
        envs = sorted(
            blurdev.activeEnvironment().environments, key=lambda i: i.objectName()
        )
        for e in envs:
            rows.append(
                (
                    e.objectName(),
                    'X' if e.isActive() else '',
                    'X' if e.isDefault() else '',
                )
            )
        click.echo(tabulate(rows, headers=['Name', 'Active', 'Default']))
