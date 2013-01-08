##
#   :namespace  python.blurdev.gui.widgets.pyularwidget.regexrefdialog
#
#   :remarks
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       11/11/11
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
    <tr>
        <td><b><code>(?P&lt;name&gt;...)</code></b></td><td>Group subpattern and capture into named group</td>
        <td><b><code>(?P=name)</code></b></td><td>Matches whatever text was matched by the earlier group named name. See (?P&lt;name&gt;...).</td>
        <td><b><code>(?=...)</code></b></td><td><i><u>Lookahead assertion:</i></u> Matches if ... matches next, but doesn't consume any of the string.</td>
    </tr>
    <tr>
        <td><b><code>(?!...)</code></b></td><td><i><u>Negative Lookahead Assertion:</i></u> Matches if ... doesn't match next.</td>
        <td><b><code>(?&gt;=...)</code></b></td><td width=27%><i><u>Positive Lookbehind Assertion:</i></u> Matches if the current position in the string is preceded by a match for ... that ends at the current position.</td>
        <td><b><code>(?&gt;!...)</code></b></td><td width=27%><i><u>Negative Lookbehind Assertion:</i></u> Matches if the current position in the string is not preceded by a match for ...</td>
    </tr>
    <tr>
        <td><b><code>(?:...)</code></b></td><td>Groups Subpattern, but does not capture submatch</td>
        <td><b><code></code></b></td><td width=27%><i><u></i></u></td>
        <td><b><code></code></b></td><td width=27%><i><u></i></u></td>
    </tr>
</table>'''

flagsHtml = '''<table>
    <tr>
        <td><b>I </b></td><td>Ignore Case  </td><td>Perform case-insensitive matching; expressions like [A-Z] will match lowercase letters, too. This is not affected by the current locale.</td>
    </tr>
    <tr>
        <td><b>L </b></td><td>Locale</td><td>Make \w, \W, \b, \B, \s and \S dependent on the current locale.</td>
    </tr>
    <tr>
        <td><b>M </b></td><td>Multiline</td><td>When specified, the pattern character '^' matches at the beginning of the string and at the beginning of each line (immediately following each newline); and the pattern character '$' matches at the end of the string and at the end of each line (immediately preceding each newline). By default, '^' matches only at the beginning of the string, and '$' only at the end of the string and immediately before the newline (if any) at the end of the string.</td>
    </tr>
    <tr>
        <td><b>S </b></td><td>DOTALL</td><td>Make the '.' special character match any character at all, including a newline; without this flag, '.' will match anything except a newline.</td>
    </tr>
    <tr>
        <td><b>U </b></td><td>UNICODE</td><td>Make \w, \W, \b, \B, \d, \D, \s and \S dependent on the Unicode character properties database.</td>
    </tr>
    <tr>
        <td><b>X </b></td><td>VERBOSE</td><td>This flag allows you to write regular expressions that look nicer. Whitespace within the pattern is ignored, except when in a character class or preceded by an unescaped backslash, and, when a line contains a '#' neither in a character class or preceded by an unescaped backslash, all characters from the leftmost such '#' through the end of the line are ignored.</td>
    </tr>
</table>
'''


class RegexRefDialog(Dialog):
    def __init__(self, parent=None):
        super(RegexRefDialog, self).__init__(parent)

        # load the ui
        import blurdev

        blurdev.gui.loadUi(__file__, self)
