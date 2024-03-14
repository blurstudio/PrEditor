import os

import pytest

from preditor.utils.text_search import RegexTextSearch, SimpleTextSearch


def text_for_test(filename):
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, filename)
    with open(filename) as fle:
        return fle.read()


@pytest.mark.parametrize(
    "check_type,search_text,is_cs,context,is_re",
    (
        # Simple text search testing context and case
        ("simple", "search term", False, 0, False),
        ("simple", "search term", False, 1, False),
        ("simple", "search term", False, 2, False),
        ("simple", "search term", False, 3, False),
        ("simple", "search term", True, 2, False),
        # Regex search testing context and case
        ("re_simple", "search term", False, 0, True),
        ("re_simple", "search term", False, 2, True),
        ("re_simple", "search term", False, 3, True),
        ("re_simple", "search term", True, 2, True),
        # Complex regex with a greedy search term
        ("re_greedy", "search.+term", False, 0, True),
        ("re_greedy", "search.+term", False, 2, True),
        ("re_greedy", "search.+term", True, 2, True),
        ("re_greedy_upper", "Search.+term", True, 2, True),
    ),
)
def test_find_files(capsys, check_type, search_text, is_cs, context, is_re):
    workbox_id = "1,2"
    path = 'First Group/First Tab'
    text = text_for_test("tab_text.txt")

    if is_re:
        TextSearch = RegexTextSearch
    else:
        TextSearch = SimpleTextSearch

    search = TextSearch(search_text, case_sensitive=is_cs, context=context)
    # Add the title to the printed output so title is tested when checking
    # `captured.out` later.
    print(search.title())

    # Generate the search text and print it to `captured.out` so we can check
    search.search_text(text, path, workbox_id)

    captured = capsys.readouterr()
    check_filename = "{}_{}_{}_{}.md".format(check_type, is_cs, context, is_re)
    check = text_for_test(check_filename)

    # To update tests, print text and save over top of the md. Then verify
    # that it is actually rendered properly. You will need to add one trailing
    # space after dot lines, two spaces after blank lines, and ensue the end of
    # file newline is present. The default print callbacks use markdown links,
    # but don't really render valid markdown. If you want to render to html,
    # use regular markdown not github flavored.
    # print(check_filename)
    # print(captured.out)

    # print('*' * 50)
    # for line in check.rstrip().splitlines(keepends=True):
    #     print([line])
    # print('*' * 50)
    # for line in captured.out.splitlines(keepends=True):
    #     print([line])

    assert captured.out == check
