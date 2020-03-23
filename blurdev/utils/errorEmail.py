''' Install the blur error handler '''
# pylint:disable=no-member,wrong-import-order,ungrouped-imports,too-many-branches,too-many-nested-blocks,too-many-locals,too-many-arguments
import blurdev
import os, sys, re, smtplib, socket, getpass, platform, datetime
from blurdev.contexts import ErrorReport
from blurdev import debug


_HTML_TEMPLATE = """<div style="background:white;color:red;padding:5 10 5 10;border:1px black solid"><pre><code>
%(code)s
</code></pre></div>"""


_EMAIL_FORMAT = """
<html>
    <head>
        <style>
            body {
                font-family: Verdana, sans-serif;
                font-size: 12px;
                color:#484848;
                background:lightGray;
            }
            h1, h2, h3 { font-family: "Trebuchet MS", Verdana, sans-serif; margin: 0px; }
            h1 { font-size: 1.2em; }
            h2, h3 { font-size: 1.1em; }
            a, a:link, a:visited { color: #2A5685;}
            a:hover, a:active { color: #c61a1a; }
            a.wiki-anchor { display: none; }
            hr {
                width: 100%%;
                height: 1px;
                background: gray;
                border: 0;
            }
            .footer {
                font-size: 0.9em;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <h1>%(subject)s</h1>
        <br>
        %(body)s
        <br><br>
        <hr/>
        <span class="footer">
            <p>%(datestamp)s</p>
            <p>You have received this notification because you have either subscribed to it, or are involved in it.<br/>
            To change your notification preferences, go into trax and change your options settings.
            </p>
        </span>
    </body>
</html>
"""

_ADDITIONAL_INFO_HTML = """<br><h3>ErrorReport: %(title)s</h3>
<br>
<div style="background:white;padding:5 10 5 10;border:1px black solid"><pre><code>
%(info)s
</code></pre></div>"""

_ADDITIONAL_INFO_TEXTILE = """h3. ErrorReport: %(title)s

<pre><code class="Python">
%(info)s
</code></pre>"""


_INFO_LIST_ITEM_HTML = "<li><b>%(key)s:</b> %(value)s</li>"

_MESSAGE_BODY_HTML = """<ul>
%(infoList)s
</ul>
<br>
<h3>Traceback Printout</h3>
<br>
%(error)s
%(additionalinfo)s"""

_INFO_LIST_ITEM_TEXTILE = "* *%(key)s:* %(value)s"

_MESSAGE_BODY_TEXTILE = """%(infoList)s

h3. Traceback Printout

<pre><code class="Python">
%(error)s</code></pre>

%(additionalinfo)s"""

_INFO_LIST_ITEM_PLAIN = "%(key)s: %(value)s"

_MESSAGE_BODY_PLAIN = """%(infoList)s

Traceback Printout

%(error)s

%(additionalinfo)s"""


def insertLineNumbers(html):
    ''' Insert line numbers into the html formatting '''
    match = re.search('(<pre[^>]*>)(.*)(</pre>)', html, re.DOTALL)
    if not match:
        return html

    preOpen = match.group(1)
    pre = match.group(2)
    preClose = match.group(3)

    html = html.replace(preClose, '</pre></td></tr></table>')
    numbers = range(1, pre.count('\n') + 1)
    fmt = '%' + str(len(str(numbers[-1]))) + 'i'
    lines = '\n'.join(fmt % i for i in numbers)
    html = html.replace(
        preOpen, '<table><tr><td>' + preOpen + lines + '</pre></td><td>' + preOpen
    )
    return html


def highlightCodeHtml(code, lexer, style, linenos=False, divstyles=None):
    ''' Add python hilighting to the html output '''
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter
    except ImportError, e:
        print('Could not import pygments, using old html formatting: {}'.format(e))
        return _HTML_TEMPLATE % {'code': code.replace('\n', '<br>')}

    lexer = lexer or 'python'
    style = style or 'colorful'
    defstyles = 'overflow:auto;width:auto;'
    if not divstyles:
        divstyles = (
            'border:solid gray;border-width:.1em .1em .1em .8em;padding:.2em .6em;'
        )

    formatter = HtmlFormatter(
        style=style,
        linenos=False,
        noclasses=True,
        cssclass='',
        cssstyles=defstyles + divstyles,
        prestyles='margin: 0',
    )
    html = highlight(code, get_lexer_by_name(lexer), formatter)
    if linenos:
        html = insertLineNumbers(html)
    return html


def buildErrorMessage(error, subject=None, information=None, fmt='html'):
    """
    Generates a email of the traceback, and useful information provided by the class if available.

        If the erroring class provides the following method,
        any text it returns will be included in the message under Additional Information
        |	def errorLog(self):
        |		return '[Additional text to include in email]'

    :param error: The error message to pass along
    :param information: if provided this string is included under the Information header of the provided email
    """
    if not error:
        return None, None

    # get current user
    username = getpass.getuser()
    if not username:
        username = 'Anonymous'

    # get current host
    try:
        host = socket.gethostname()
    except socket.error:
        host = 'Unknown'

    # Build the message
    envName = blurdev.activeEnvironment().objectName()
    minfo = {}
    from collections import OrderedDict

    infoList = OrderedDict()
    infoList['username'] = username
    infoList['hostname'] = host
    infoList['date'] = datetime.datetime.now().strftime('%b %d, %Y @ %I:%M %p')
    infoList['python version'] = sys.version.replace('\n', '')
    infoList['platform'] = platform.platform()
    infoList['executable'] = sys.executable
    # Include Assburner job info if available
    jobKey = os.environ.get('AB_JOBID')
    if jobKey:
        infoList['assburner job id'] = jobKey
    burnDir = os.environ.get('AB_BURNDIR')
    if burnDir:
        infoList['assburner burn dir'] = burnDir
    burnFile = os.environ.get('AB_BURNFILE')
    if burnFile:
        infoList['assburner burn file'] = burnFile

    infoList['blurdev core'] = blurdev.core.objectName()
    infoList['blurdev env'] = '%s: %s' % (envName, blurdev.activeEnvironment().path())

    # notify where the error came from
    if blurdev.core.headless:
        window = None
    else:
        from Qt.QtWidgets import QApplication

        window = QApplication.activeWindow()
    className = ''

    # use the root application
    if window.__class__.__name__ == 'LoggerWindow':
        window = window.parent()
    elif window.__class__.__name__ == 'ErrorDialog':
        window = window.parent()

    if window:
        infoList['window'] = '%s (from %s Class)' % (
            window.objectName(),
            window.__class__.__name__,
        )
        className = '[W:%s]' % window.__class__.__name__

    # Build the brief & subject information
    if not subject:
        subject = error.split('\n')[-2]
        # Limit the subject line to less than 400 characters excluding the filter info. This
        # prevents especially long subjects like those generated by a sql error.
        if len(subject) > 400:
            subject = '{} ...'.format(subject[:400])
    if envName:
        envName = '[E:%s]' % envName

    subject = '[Python Error][U:%s][C:%s]%s%s %s' % (
        username,
        blurdev.core.objectName(),
        envName,
        className,
        subject,
    )

    coreMsg = blurdev.core.errorCoreText()

    if coreMsg:
        infoList['blurdev.core Message'] = coreMsg

    # Load in any aditional error info from the environment variables
    prefix = 'BDEV_EMAILINFO_'
    for key in sorted(os.environ):
        if key.startswith(prefix):
            infoList[key[len(prefix) :].replace('_', ' ').lower()] = os.environ[key]

    if fmt == 'html':
        errorstr = highlightCodeHtml(unicode(error), 'pytb', 'default')
    else:
        errorstr = unicode(error)
    minfo['error'] = errorstr

    # append any passed in body text, and any ErrorReport text.
    minfo['additionalinfo'] = ''
    infos = [(None, information)] + ErrorReport.generateReport()
    for title, info in infos:
        if info is not None:
            if fmt == 'html':
                formatData = {
                    'info': unicode(info).replace('\n', '<br>'),
                    'title': title,
                }
                addinfo = _ADDITIONAL_INFO_HTML % formatData
            elif fmt == 'textile':
                addinfo = _ADDITIONAL_INFO_TEXTILE % {
                    'info': unicode(info),
                    'title': title,
                }
            else:
                addinfo = unicode(info)
            minfo['additionalinfo'] += addinfo

    # append extra stuff
    if hasattr(sys, 'last_traceback'):
        tb = sys.last_traceback
        if tb:
            frame = tb.tb_frame
            if frame:
                module = frame.f_locals.get('self')
                if module:
                    if hasattr(module, 'errorLog'):
                        try:
                            errorlog = module.errorLog()
                        except Exception, e:  # pylint:disable=broad-except
                            modulename = frame.f_globals.get('__name__')
                            if not modulename:
                                modulename = 'module'
                            errorlog = '%s.errorLog() generated an error: %s' % (
                                modulename,
                                str(e),
                            )
                        if fmt == 'html':
                            addinfo = _ADDITIONAL_INFO_HTML % {
                                'info': unicode(errorlog).replace('\n', '<br>')
                            }
                        elif fmt == 'textile':
                            addinfo = _ADDITIONAL_INFO_TEXTILE % {
                                'info': unicode(errorlog)
                            }
                        else:
                            addinfo = unicode(errorlog)
                        minfo['additionalinfo'] += addinfo

    def _joinInfoList(formatter):
        return '\n'.join(
            [
                formatter % {'key': key, 'value': value}
                for key, value in infoList.iteritems()
            ]
        )

    if fmt == 'html':
        minfo['infoList'] = _joinInfoList(_INFO_LIST_ITEM_HTML)
        message = _MESSAGE_BODY_HTML % minfo
    elif fmt == 'textile':
        minfo['infoList'] = _joinInfoList(_INFO_LIST_ITEM_TEXTILE)
        message = _MESSAGE_BODY_TEXTILE % minfo
    else:
        minfo['infoList'] = _joinInfoList(_INFO_LIST_ITEM_PLAIN)
        message = _MESSAGE_BODY_PLAIN % minfo
    return subject, message


def emailError(emails, error, subject=None, information=None):
    ''' Send an email on an error '''
    if not error:
        return

    # do not email when debugging
    if debug.debugLevel():
        return

    subject, message = buildErrorMessage(error, subject, information)
    try:
        sender = blurdev.core.emailAddressMd5Hash(subject)
        # Prevent gmail from ... "trimming" the entire email contents due to each message
        # being almost identical.
        datestamp = datetime.datetime.now().strftime('%b %d, %Y @ %I:%M %p')

        msg = _EMAIL_FORMAT % {
            'subject': subject,
            'body': message,
            'datestamp': datestamp,
        }
        blurdev.core.sendEmail(sender, emails, subject, msg)
    except socket.error:
        # Unable to send error email. It is assumed you don't have a valid email addres.
        pass
    except smtplib.SMTPException as e:
        print('Error connecting to smtp server: {}'.format(e))
        print('email not sent')
