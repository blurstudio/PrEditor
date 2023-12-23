from __future__ import print_function

from collections import deque

from Qt.QtWidgets import QWidget

from ..gui import loadUi


class FindFiles(QWidget):
    def __init__(self, managers=None, parent=None):
        super(FindFiles, self).__init__(parent=parent)
        if managers is None:
            managers = []
        self.managers = managers

        loadUi(__file__, self)

    def insert_found_text(self, found_text, href, tool_tip):
        cursor = self.console.textCursor()
        # Insert hyperlink
        fmt = cursor.charFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(href)
        fmt.setFontUnderline(True)
        fmt.setToolTip(tool_tip)
        cursor.insertText(found_text, fmt)

    def insert_text(self, text):
        cursor = self.console.textCursor()
        fmt = cursor.charFormat()
        fmt.setAnchor(False)
        fmt.setAnchorHref('')
        fmt.setFontUnderline(False)
        fmt.setToolTip('')
        cursor.insertText(text, fmt)

    def indicate_results(
        self,
        line,
        line_num,
        find_text="undefined",
        path="undefined",
        workbox_id="undefined",
        fmt="",
    ):
        href = '{}, {}, {}'.format(path, workbox_id, line_num)
        tool_tip = "Open {} at line number {}".format(path, line_num)
        find_len = len(find_text)

        start = 0
        line = fmt.format(
            num=line_num, split=" " if line.find(find_text) == -1 else ":", line=line
        )
        end = line.find(find_text)
        count = 0
        while end != -1:
            # insert prefix text
            self.insert_text(line[start:end])
            # insert indicated text preserving case
            self.insert_found_text(line[end : end + find_len], href, tool_tip)
            start = end + find_len
            end = line.find(find_text, start)
            count += 1
            if count > 10:
                print('break', start, end)
                break
        if end < find_len:
            self.insert_text(line[start:])

    def print_lines(self, start, *lines, info=None):
        if info is None:
            info = {}
        info.setdefault("fmt", "  {num: 4d}{split} {line}")

        # If start is negative, set it to zero
        start = max(0, start)
        for i, line in enumerate(lines):
            # line = fmt.format(num=start + i, line=line)
            # print(line)
            self.indicate_results(line + "\n", start + i, **info)

    def search_file_simple(self, editor, path, workbox_id):
        # print('search_file_simple', path)
        context = self.uiContextSPN.value()
        find_text = self.uiFindTXT.text()
        # Ensure the editor text is loaded
        editor.__show__()
        raw_lines = editor.__text__().splitlines()
        # Add enough padding to cover the number of lines in the file
        padding = len(str(len(raw_lines)))
        fmt = "  {{num: >{}}}{{split}} {{line}}".format(padding)

        # https://stackoverflow.com/a/52009859
        pre_history = deque(maxlen=context)
        post_history = None
        post_line = None
        first = True
        for i, line in enumerate(raw_lines):
            # Lines are 1 based indexes
            i += 1
            info = dict(find_text=find_text, fmt=fmt, path=path, workbox_id=workbox_id)
            if find_text in line:
                ii = i - context
                if first:
                    # Print the filename on the first find
                    print("# File: {}".format(path))
                    first = False
                else:
                    print(
                        "  {dot: >{padding}} ".format(
                            dot='.' * len(str(ii)), padding=padding
                        )
                    )
                self.print_lines(ii, *pre_history, line, info=info)
                # print(" xxx:", *pre_history, line, sep='')
                # Clear history so if two errors seen in close proximity, we don't
                # echo some lines twice
                pre_history.clear()
                # Start recording the post context
                post_history = deque(maxlen=context)
                post_line = i + 1
            else:
                # When deque reaches 25 lines, will automatically evict oldest
                pre_history.append(line)
                # Add the line to the post history after we find a result.
                if post_history is not None:
                    post_history.append(line)
                    # Once we exceed context without finding another result,
                    # print the post text and stop tracking post_history
                    if len(post_history) >= context:
                        self.print_lines(post_line, *post_history, info=info)
                        post_history = None
                        post_line = None

        if post_history:
            print('# --------')
            self.print_lines(post_line, *post_history, info=info)

    def find(self):
        find_text = self.uiFindTXT.text()
        print("Find:", find_text)

        for manager in self.managers:
            for (
                editor,
                group_name,
                tab_name,
                group_index,
                tab_index,
            ) in manager.all_widgets():
                path = "/".join((group_name, tab_name))
                workbox_id = '{},{}'.format(group_index, tab_index)
                self.search_file_simple(editor, path, workbox_id)
