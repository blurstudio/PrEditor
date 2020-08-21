##
# 	\namespace	linux-2011-07-19.ide.ideaboutdialog
#
# 	\remarks	Simple About dialog to show the data from the editor
#
# 	\author		[author::email]
# 	\author		[author::company]
# 	\date		07/21/11
#

from blurdev.gui import Dialog

HTML_TEMPLATE = """
<html>
    <body>
        <p align="center"><h2>blurdev IDE</h2>
            <br><small>version | %(version)s</small>
        </p>
        <p align="center"><b>credits</b>
        <hr/><table padding="10" spacing="10">
            <tr><td colspan="3"></tr>
            %(credits)s
        </table>
        <br>
        <hr/>
        <p>
            The blurdev IDE is an editing system designed and developed at Blur Studio
            in Venice, CA, 2010.  The original goal for the project was to create a
            system which was easily expandable, making it simple to create and maintain
            coding standards.
            <br/><br/>
            The other purpose for the IDE was to provide a cross-platform,
            cross-application editor that works not only on multiple platforms, but that
            can run as a standalone application as well as an application running inside
            of DCC applications such as 3dsMax and Softimage.

        </p>
    </body>
</html>
"""


class IdeAboutDialog(Dialog):
    def __init__(self, parent=None):
        super(IdeAboutDialog, self).__init__(parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)

        credits = [
            ('Eric Hulser', 'eric@blur.com', 'Project Manager/Lead Developer'),
            ('Mike Hendricks', 'mikeh@blur.com', 'Lead Developer'),
            ('Brendan Abel', 'brendana@blur.com', 'Developer'),
            ('Matt Newell', 'newellm@blur.com', 'Qt/PyQt Support'),
            ('Liam Fernandez', 'liam@blur.com', 'Developer'),
        ]

        # create the about html
        options = {}
        options['version'] = blurdev.version.to_string()
        options['credits'] = ''.join(
            [
                (
                    '<tr><td>%s</td><td> . </td><td align="center">%s</td><td> . '
                    '</td><td>%s</td>'
                ) % credit
                for credit in credits
            ]
        )

        self.uiAboutTXT.setHtml(HTML_TEMPLATE % options)
