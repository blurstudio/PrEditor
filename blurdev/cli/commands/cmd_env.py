import blurdev
import click
from tabulate import tabulate


@click.group()
def cli():
    """ Manage treegrunt environments. """
    pass


@cli.command()
@click.argument('env')
@click.option(
    '-c',
    '--core-name',
    default='external',
    help="Set the active environment for this core name.",
)
def activate(env, core_name):
    """ Change the currently selected treegrunt environment """

    success = blurdev.activeEnvironment(coreName=core_name) == env
    if not success:
        # This returns false if env is already active
        success = blurdev.setActiveEnvironment(env, coreName=core_name)

    if success:
        msg = 'Set active environment: {env} for core name: {core}'
    else:
        msg = 'Unable to set the active environment {env} for core name {core}'
    click.echo(msg.format(env=env, core=core_name))


@cli.command()
@click.option(
    '-c',
    '--core-name',
    default='external',
    help="Get the currently active environment for this core name.",
)
def active(core_name):
    """ Returns the currently selected treegrunt environment """
    click.echo(
        'Active Environment: {} for core name: {}'.format(
            blurdev.activeEnvironment(coreName=core_name).objectName(), core_name
        )
    )


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
