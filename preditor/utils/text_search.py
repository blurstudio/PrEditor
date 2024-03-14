from __future__ import absolute_import, print_function

import abc
import re
from collections import deque

from future.utils import with_metaclass


class TextSearch(with_metaclass(abc.ABCMeta, object)):
    """Base class used to search and markup text for matches to a search term.

    Parameters:
        callback_matching (callable): Called when matching text should be written.
            See `print_matching` to see what inputs it must accept.
        callback_non_matching (callable): Called when plain text should be written.
            See `print_non_matching` to see what inputs it must accept.
        gap_format (str): A format string used to indicate when there is a gap in
            the results shown. These variables are provided when formatting. `dot`
            `dot` is a `.` for each digit required to show the current line number.
            `padding` can be used to properly pad `dot`.
        margin_format (str): A format string used to generate the line number
            text at the start of a text line. These variables are provided when
            formatting. `line_num` the current line number as an int. `padding`
            can be used to properly pad `line_num`. `match_indicator` is a string
            that is a `:` if the line contains a match, otherwise an empty space.
        match_count (int): The number times matching text was found including
            multiple finds on the same line. This value is not reset internally
            and can be used to track all matches across multiple calls of `search_text`.
        padding (int): Set by `search_text` to the number of digits required to
            show all line numbers in the document. Used to ensure consistent number
            padding for all line numbers printed in the margin and gaps.

    Args:
        find_text (str): The text this finder will search for.
        case_sensitive (bool): When searching text should it ignore case.
        context (int): The number of lines to show before and after a line with
            a match.
    """

    def __init__(self, find_text, case_sensitive=False, context=3):
        self._padding = 0
        self.case_sensitive = case_sensitive
        self.context = context
        self.find_text = find_text
        self.gap_format = "  {dot: >{padding}} \n"
        self.margin_format = "  {line_num: >{padding}}{match_indicator} "
        self.match_count = 0

        self.callback_matching = self.print_matching
        self.callback_non_matching = self.print_non_matching

    def clear_cache(self):
        """The finder can implement this to clear any cached data.

        This is called when no matches have been found beyond the # of context lines
        """

    @abc.abstractmethod
    def indicate_line(self, line):
        """Yields chunks of line and if each chunk should be indicated.

        The first yield should always be `(None, bool)`. The None value indicates
        that the margin should be printed. This triggers printing of `self.margin`
        passing the bool to the match_found argument.

        Yields:
            text (str or None): The text to be printed.
            indicate (bool): Should text treated as a match for the search term.
        """

    def indicate_results(
        self, line, line_num, path="undefined", workbox_id="undefined"
    ):
        """Writes a single line adding markup for any matches on the line."""
        tool_tip = "Open {} at line number {}".format(path, line_num)
        for text, indicate in self.indicate_line(line):
            # Print the margin text after the finder tells us if the line matches
            if text is None:
                self.callback_non_matching(self.margin(line_num, indicate))
                continue

            # Otherwise print the next section of the line text
            if indicate:
                self.callback_matching(text, workbox_id, line_num, tool_tip)
            else:
                self.callback_non_matching(text)

    def insert_lines(self, start, *lines, info):
        """Inserts multiple lines adding links for any matching search terms.

        Args:
            start (int): The line number of the first line to insert.
            *lines (str): Each line to insert. They will be prefixed with line
                numbers starting with start.
            info (dict): Kwargs passed to indicate_results.

        Returns:
            int: The line number of the last line that was inserted.
        """
        for i, line in enumerate(lines):
            # Note: The `+ 1` is due to line numbers being 1 based not zero based
            self.indicate_results(line, start + i + 1, **info)

        return start + i

    def margin(self, line_num, match_found):
        """Returns the margin text rendered and ready to print.

        Args:
            line_num (int): The line number to show in the margin.
            match_found (bool): Controls the indicator of if this line has any
                matching text. If True then a `:` is inserted otherwise a space.
        """
        match_indicator = ":" if match_found else " "
        return self.margin_format.format(
            line_num=line_num, match_indicator=match_indicator, padding=self._padding
        )

    @abc.abstractmethod
    def matches(self, line):
        """Returns bool for if find_text is contained in this line."""

    def print_matching(self, text, workbox_id, line_num, tool_tip):
        """Simple callback for `callback_matching` that prints text.

        The print does not insert an newline character.

        Args:
            text (str): The matching text to display. This will be inserted
                into a markdown link as the link text.
            workbox_id (str): From `GroupTabWidget.all_widgets`, the group_tab_index
                and widget_tab_index joined by a comma without a space. Used as
                the url of the link. Example: `3,1`.
            line_number (int): The line number the url should navigate to.
            tool_tip (str): Added as a title to the link to show up as a tool tip.
        """
        href = ', {}, {}'.format(workbox_id, line_num)
        print('[{}]({} "{}")'.format(text, href, tool_tip), end="")

    def print_non_matching(self, text):
        """Simple callback for `callback_non_matching` that prints text.

        The print does not insert an newline character.
        """
        print(text, end="")

    def search_text(self, text, path, workbox_id):
        """Search each line of text for matching text and write the the matches
        including context lines.

        Args:
            text (str): The text to search.
            path (str): The workbox name this text represents. Should be the
                Group_name and tab_name separated by a `/`.
            workbox_id (str): From `GroupTabWidget.all_widgets`, the group_tab_index
                and widget_tab_index joined by a comma without a space. Used as
                the url of the link. Example: `3,1`.
        """
        # NOTE: splitlines discards the "newline at end of file" so it doesn't
        # show up in the final search results.
        lines = text.splitlines(keepends=True)

        # Calculate the padding count so we can ensure all line numbers and gaps
        # are consistently spaced in the margins.
        self._padding = len(str(len(lines)))

        # Buffer to record up to context lines of text. This will be printed
        # only if we find a match in the middle of the document.
        # https://stackoverflow.com/a/52009859
        pre_history = deque(maxlen=self.context)
        remaining_context_lines = 0

        # last_insert keeps track of the last time we inserted a line. This lets
        # us keep track of if there is a gap in output and we need to add dots.
        last_insert = 0
        found = False

        for i, line in enumerate(lines):
            info = dict(path=path, workbox_id=workbox_id)
            if self.matches(line):
                len_pre_history = len(pre_history)
                if not found:
                    # Print the path on the first find
                    self.callback_non_matching("# File: ")
                    tool_tip = "Open {}".format(path)
                    self.callback_matching(path, workbox_id, 0, tool_tip)
                    self.callback_non_matching("\n")
                    found = True
                elif i - last_insert - 1 - len_pre_history > 0:
                    # If there is a in output larger than context, insert dots
                    # for the width of the line numbers to indicate the gap.
                    self.callback_non_matching(
                        self.gap_format.format(
                            dot='.' * len(str(i)), padding=self._padding
                        )
                    )
                # Add the matching line the pre-context of the matching line.
                last_insert = self.insert_lines(
                    i - len_pre_history, *pre_history, line, info=info
                )
                # Reset the pre-context history now that we have printed it.
                pre_history.clear()
                # Reset the post context line count so we will print the full
                # context after this latest match if no other matches are found.
                remaining_context_lines = self.context
            else:
                if remaining_context_lines > 0:
                    # Print any remaining context lines after we found a result
                    last_insert = self.insert_lines(i, line, info=info)
                    remaining_context_lines -= 1
                else:
                    # If we don't need to print any post context lines record
                    # this line into pre-context history so we can print it if
                    # we find a match on the next line.
                    # When deque reaches maxlen lines, it automatically evicts oldest
                    pre_history.append(line)
                    # Clear any cached match information the finder may have stored.
                    self.clear_cache()

        # Return if this file contained any matches
        return found

    def title(self):
        return '\nFind in workboxs: "{}"{}\n\n'.format(self.find_text, self.title_flags)

    @property
    @abc.abstractmethod
    def title_flags(self):
        """Returns the text to show in the title for flags."""


class RegexTextSearch(TextSearch):
    """TextSearch that processes the text using regex."""

    def __init__(self, find_text, case_sensitive=False, context=3):
        super(RegexTextSearch, self).__init__(
            find_text, case_sensitive, context=context
        )
        self.pattern = re.compile(find_text, flags=0 if case_sensitive else re.I)
        # Cache regex match objects between the `matches` call and `indicate_line`
        # The key is the original line of text
        self._matches = {}

    def clear_cache(self):
        # Reset regex cache for the next call to `matches`
        self._matches = {}

    def indicate_line(self, line):
        # Check if this line is a match.
        match = self._matches.get(line)
        # Write the margin indicating if this line has any matches
        yield None, bool(match)

        start = 0
        if match:
            for m in match:
                pre = line[start : m.start()]
                if pre:
                    yield pre, False
                yield line[m.start() : m.end()], True
                start = m.end()
                # Record the match
                self.match_count += 1
            post = line[start:]
            if post:
                yield post, False
        else:
            yield line, False

    def matches(self, line):
        self._matches[line] = list(self.pattern.finditer(line))
        return bool(self._matches[line])

    @property
    def title_flags(self):
        if self.case_sensitive:
            return " (regex, case sensitive)"
        return " (regex)"


class SimpleTextSearch(TextSearch):
    """A simple text matching finder that optionally considers case."""

    def __init__(self, find_text, case_sensitive=False, context=3):
        super(SimpleTextSearch, self).__init__(
            find_text, case_sensitive, context=context
        )
        # Assign the correct matching method based on the desired case setting
        if case_sensitive:
            self._matches = self._search_text_case_sensitive
        else:
            self._matches = self._search_text
            find_text = self.find_text.lower()
        # Preserve the original find_text value but cache the value needed internally
        self._find_text = find_text

    def _search_text(self, line):
        """Check for pattern ignoring case."""
        return self._find_text in line.lower()

    def _search_text_case_sensitive(self, line):
        """Check for pattern matching case."""
        return self._find_text in line

    def indicate_line(self, line):
        # Handle case sensitivity setting, ensuring return of the correct case
        original_line = line
        if not self.case_sensitive:
            line = line.lower()

        find_len = len(self._find_text)
        start = 0
        end = line.find(self._find_text)
        # Write the margin indicating if this line has any matches
        yield None, end != -1

        # Write the text of the line with indications
        while end != -1:
            # insert prefix text
            yield original_line[start:end], False
            # insert indicated text preserving case
            yield original_line[end : end + find_len], True
            # Record the match
            self.match_count += 1

            # Check for any more matches in this line
            start = end + find_len
            end = line.find(self._find_text, start)

        # Include text at the end of the line
        if end < find_len:
            yield original_line[start:], False

    def matches(self, line):
        return self._matches(line)

    @property
    def title_flags(self):
        if self.case_sensitive:
            return " (case sensitive)"
        return ""
