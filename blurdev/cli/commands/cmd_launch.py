""" Run a external treegrunt tool.

By default this will just launch the tool without any extra cli options. If you want
to change this you can add a python module in your tool folder and add a `<cliModule>`
tag to the tool's __meta__.xml. This tag should contain the path to import the cli
module. The cli module should have a cli function that implements its command line
interface using the click package.
"""
from __future__ import absolute_import
import click
import blurdev
import os
from tabulate import tabulate


class LaunchAlias(click.Group):
    """Lazily handle the cli for the requested tool id."""

    def get_command(self, ctx, name):
        tool = blurdev.findTool(name)
        # Handle invalid  and list command
        if tool.isNull():
            # Handle invalid tool name
            return list_tools

        # return the tool cli
        try:
            mod_name = tool.cli_module()
            if mod_name:
                # Attempt to load the cli definition for the tool if possible
                mod = __import__(mod_name, None, None, ["cli"])
                return mod.cli
        except ImportError:
            pass

        # No tool specific cli was defined use the generic launch_tool command.
        # Store the name of the tool on the group context. This can be accessed
        # in launch_tool on its ctx parent(ctx.parent.tool).
        ctx.tool = name
        return launch_tool


@click.command(cls=LaunchAlias)
def cli():
    """Run the tool based on the given tool id"""


@click.command()
@click.pass_context
def launch_tool(ctx):
    """Run the requested external treegrunt tool"""
    # Generic tool loader if no cli for the tool was defined

    # Get the tool id from the parent context
    tool = ctx.parent.tool

    # Use the toolId as the applicationName. When blurdev is imported, it will
    # set the ApplicationName to match this toolname.
    blurdev.core.updateApplicationName(name=tool)

    if 'BDEV_TOOL_ENVIRONMENT' not in os.environ:
        # Use the external environment that is used by external treegrunt.
        # This way desktop shortcuts always point to this environment.
        pref = blurdev.prefs.find('blurdev/core', coreName='external', reload=True)
        # With this set, the treegrunt environment will always be this environment
        # in this process even if the core prefs want to load a different environment.
        # It also prevents changing the core's environment if core.shutdown() is called.
        os.environ['BDEV_TOOL_ENVIRONMENT'] = blurdev.settings.environStr(
            pref.restoreProperty('environment', '')
        )

    # blurdev.launch will call this automatically. By setting it here, we prevent a
    # known bug where tool class objects get reset to None and the tool fails to launch.
    blurdev.core.setObjectName('external')

    # Do not launch the tool as a subprocess. This ends up wasting time creating a new
    # python subprocess, and re-importing python modules. Once the requested tool is
    # launched, this value will get set to True so any tools launched after this will
    # happen in a new process.
    blurdev.core.launchExternalInProcess = 'once'

    # launch the editor
    blurdev.runTool(tool)


@cli.command('list')
@click.argument('search', required=False)
def list_tools(search):
    """Show a list of tools that can be launched externally. Tool Id is the command
    you pass to "blurdev launch [Tool Id]".

    The  optional search term can be specified to filter the results in the same way
    treegrunt's search feature works.
    """
    index = blurdev.activeEnvironment().index()
    # Force the index to load so we get access to all of the tools
    index.load()
    # Get tool names only for the tool
    if search:
        tools = index.search(search)
    else:
        tools = sorted(index.tools(), key=lambda i: i.objectName())

    tool_types = blurdev.core.selectedToolTypes()
    rows = [
        (tool.objectName(), tool.displayName())
        for tool in tools
        if tool.toolType() & tool_types
    ]

    click.echo(tabulate(rows, headers=['Tool Id', 'Display name']))
    click.echo('    {} tools found'.format(len(rows)))
