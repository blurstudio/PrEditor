""" The blurdev command line interface. Can be accessed with the ``blurdev`` or
``blurdevw`` command to disable the python console showing up on windows.

Adding new commands:
    New commands can be added by adding a file in the commands sub-folder that
    startswith `cmd_` and has the `.py` file extension. The file should have a
    `@click.command` or `@click.group` decorated function called `cli`.

    Example plugin code::

        import click

        @click.command()
        @click.option('--name', prompt='Your name', help='The person to greet.')
        def cli(name):
            '''Simple program that greets NAME for a total of COUNT times.'''
            click.echo('Hello %s!' % name)

    If you save this code as 'commands/cmd_hello.py' you can run it::

        $ blurdev hello --help
        Usage: blurdev hello [OPTIONS]

          Simple program that greets NAME for a total of COUNT times.

        Options:
          --name TEXT  The person to greet.
          --help       Show this message and exit.

    Notice how the function docstring is used as the general help text. It is
    recommended that you use `click.echo` instead of print in cli code.
"""

from __future__ import print_function
import os
import click

# Note: This script is launched by entry points so blurdev has already been imported
import blurdev

cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))
# No one wants to actually type `--help`
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class CommandLoader(click.MultiCommand):
    """ Automatically imports all `commands/cmd_*.py` files to extend the cli.
    """

    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith('.py') and filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__(
                'blurdev.cli.commands.cmd_{}'.format(name), None, None, ['cli']
            )
        except ImportError:
            raise
            return
        return mod.cli


@click.command(cls=CommandLoader, context_settings=CONTEXT_SETTINGS)
@click.option(
    '-d',
    '--debug',
    type=click.Choice(['Disabled', '0', 'Low', '1', 'Med', '2', 'High', '4']),
    help='Use this blurdev debug level for the session. This is not saved '
    'in preferences.',
)
def main(debug):
    """ Blurdev's command line interface. """

    if debug is not None:
        success = blurdev.debug.setDebugLevel(debug)
        # Most launch tools end up changing the blurdev.core.objectName() value.
        # This causes blurdev to restore the saved debug level for that core name.
        # Setting this env var disables loading and saving debug levels.
        os.environ['BDEV_DEBUG_LEVEL'] = str(blurdev.debug.debugLevel())
        if not success:
            raise ValueError("Debug argument '{}' is not valid.".format(debug))
