"""
    A URL protocol handler. In conjunction with some registry keys created in the
    installer, when a user clicks on a ``blurdev://`` hyperlink this module will be
    called and call the proper code.

    ``blurdev://[handler]/[command]?[keywordArgs]``

    handler:
        The name of the handler. Handlers are classes that process the command and
        arguments into functioning code. Some examples are TreegruntHandler, and
        TraxHandler. These are subclassed from BaseProtocolHandler.

    command (Optional depending on handler):
        A context to give the handler. TreegruntHandler uses it for the tool name.

    keywordArgs (Optional):
        Used to pass in extra keyword arguments. Arguments start with a question
        mark(?), each keyword pair is separated by a ampersand(&), each keyword is
        separated from the argument by a equal sign(=).

    Examples::

        blurdev://treegrunt/LegacyExternal::ImageLoader
        blurdev://treegrunt/LegacyExternal::ImageLoader?key=value
        blurdev://treegrunt/wtf
        blurdev://treegrunt/wtf/
        blurdev://treegrunt/wtf?key=value&key=case&a=b
        blurdev://treegrunt/MyReviews?review=2584
        blurdev://treegrunt/DailyTool?date=today&user=Mike Hendricks&item=5
        blurdev://treegrunt/DailyTool?date=today&user=Mike%20Hendricks&item=5
"""

from __future__ import print_function
from __future__ import absolute_import
import os
import click
import blurdev
import blurdev.osystem
import blurdev.debug

try:
    # Python 3 urlparse
    from urllib import parse
except ImportError:
    import urlparse as parse

from blurdev.protocols import BaseProtocolHandler
from future.utils import iteritems


@click.command()
@click.argument('url')
def cli(url):
    """Process the passed in `blurdev://...` url"""

    # Log to a file so we can debug problems.
    basepath = blurdev.osystem.expandvars(os.environ['BDEV_PATH_BLUR'])
    blurdev.debug.logToFile(
        os.path.join(basepath, 'blurdevProtocol.log'), useOldStd=True
    )

    print(
        ('Treegrunt Environment: {}'.format(blurdev.activeEnvironment().objectName()))
    )
    print(('URL: {}'.format(url)))
    if url == 'test=1':
        # Simple unit test
        _test()
    else:
        handleURL(url)


def parseURL(url):
    """Accepts a url and returns the protocol, handler, command, and parameters

    If pyeval is True, it will try to eval the param values instead of
    returning them as strings.

    """
    parsed = parse.urlsplit(url)
    # urlsplit and parse_qs don't recognize the blurdev protocol parse and capture the
    # scheme
    scheme = parsed.scheme
    if url.startswith('blurdev:'):
        # Then re-parse the url removing the blurdev: protocol if its the protocol
        parsed = parse.urlsplit(url.replace('blurdev:', ''))
    # The old parseURL code only returned lists of values if a key was used more than
    # once
    query = {}
    for key, value in iteritems(parse.parse_qs(parsed.query)):
        if len(value) == 1:
            query[key] = value[0]
        else:
            query[key] = value
    # We need to remove the leading and trailing slashes.
    command = parsed.path.strip('/')
    return (scheme, parsed.netloc, command, query)


def handleURL(url):
    protocol, handler_name, command, params = parseURL(url)
    handler = BaseProtocolHandler.findHandler(handler_name, command, params)
    if handler:
        # Use the handler name as the applicationName. Because blurdev is already
        # imported, we need to manually call updateApplicationName.
        appName = 'protocol_{}'.format(handler.command)
        blurdev.core.updateApplicationName(name=appName)

        handler.run()


def _test():
    tests = {
        # Trailing slash does not cause problems
        'blurdev://treegrunt/wtf': ('blurdev', 'treegrunt', 'wtf', {}),
        'blurdev://treegrunt/wtf/':
        # Because we are removing the trailing slash for processing this should
        # compare against 'wtf' and not 'wtf/'
        ('blurdev', 'treegrunt', 'wtf', {}),
        # ensure that legacy tool names work
        # passing parameters is not required
        'blurdev://treegrunt/LegacyExternal::ImageLoader': (
            'blurdev',
            'treegrunt',
            'LegacyExternal::ImageLoader',
            {},
        ),
        'blurdev://treegrunt/LegacyExternal::ImageLoader?key=value': (
            'blurdev',
            'treegrunt',
            'LegacyExternal::ImageLoader',
            {'key': 'value'},
        ),
        # detect multiple parameters with same name(key)
        'blurdev://treegrunt/wtf?key=value&key=case&a=b': (
            'blurdev',
            'treegrunt',
            'wtf',
            {'a': 'b', 'key': ['value', 'case']},
        ),
        'blurdev://treegrunt/MyReviews?review=2584': (
            'blurdev',
            'treegrunt',
            'MyReviews',
            {'review': '2584'},
        ),
        # Make sure the system can handle spaces and url escaped characters
        'blurdev://treegrunt/DailyTool?date=today&user=Mike Hendricks&item=5': (
            'blurdev',
            'treegrunt',
            'DailyTool',
            {'date': 'today', 'item': '5', 'user': 'Mike Hendricks'},
        ),
        # Space replaced by %20
        'blurdev://treegrunt/DailyTool?date=today&user=Mike%20Hendricks&item=5': (
            'blurdev',
            'treegrunt',
            'DailyTool',
            {'date': 'today', 'item': '5', 'user': 'Mike Hendricks'},
        ),
    }

    for url, answer in iteritems(tests):
        try:
            assert parseURL(url) == answer
        except Exception:
            print('*' * 50)
            print('URL Failed: {}'.format(url))
            print('Expected: {}'.format(answer))
            print('Result: {}'.format(parseURL(url)))
            raise
    print('All url tests passed')
