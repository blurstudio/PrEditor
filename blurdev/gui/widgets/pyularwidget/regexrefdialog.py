##
#   \namespace  python.blurdev.gui.widgets.pyularwidget.regexrefdialog
#
#   \remarks
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       11/11/11
#

from blurdev.gui import Dialog

html = '''<table>
    <tbody><tr>
        <td><b><code><>[abc]</code></b></td><td>A single character: a, b or c</td><td><b><code>.</code></b></td><td>Any single character</td><td><b><code>(...)</code></b></td><td>Capture everything enclosed</td>
    </tr>
    <tr>
        <td><b><code>[^abc]</code></b></td><td>Any single character <em>but</em> a, b, or c</td><td><b><code>\s</code></b></td><td>Any whitespace character</td><td><b><code>(a|b)</code></b></td><td>a or b</td>
    </tr>
    <tr>
        <td><b><code>[a-z]</code></b></td><td>Any single character in the range a-z</td> <td><b><code>\S</code></b></td><td>Any non-whitespace character</td><td><b><code>a?</code></b></td><td>Zero or one of a</td>
    </tr>
    <tr>
        <td><b><code>[a-zA-Z]</code></b></td><td>Any single character in the range a-z or A-Z</td><td><b><code>\d</code></b></td><td>Any digit</td><td><b><code>a*</code></b></td><td>Zero or more of a</td>
    </tr>
    <tr>
        <td><b><code>^</code></b></td><td>Start of line</td><td><b><code>\D</code></b></td><td>Any non-digit</td><td><b><code>a+</code></b></td><td>One or more of a</td>
    </tr>
    <tr>
        <td><b><code>$</code></b></td><td>End of line</td><td><b><code>\w</code></b></td><td>Any word character (letter, number, underscore)</td><td><b><code>a{3}</code></b></td><td>Exactly 3 of a</td>
    </tr>
    <tr>
        <td><b><code>\A</code></b></td><td>Start of string</td><td><b><code>\W</code></b></td><td>Any non-word character</td><td><b><code>a{3,}</code></b></td><td>3 or more of a</td>
    </tr>
    <tr>
        <td><b><code>\z</code></b></td><td>End of string</td><td><b><code>\b</code></b></td><td>Any word boundary character</td><td><b><code>a{3,6}</code></b></td><td>Between 3 and 6 of a</td>
    </tr>
</table>
<hr>
options:
        <code>i</code>: case insensitive, 
        <code>m</code>: make dot match newlines, 
        <code>x</code>: ignore whitespace in regex, 
        <code>o</code>: perform #{...} substitutions only once'''


class RegexRefDialog(Dialog):
    def __init__(self, parent=None):
        super(RegexRefDialog, self).__init__(parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)
