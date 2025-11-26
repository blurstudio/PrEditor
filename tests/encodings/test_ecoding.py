from pathlib import Path

import pytest

from preditor.gui.workbox_mixin import WorkboxMixin

this_dir = Path(__file__).parent


@pytest.mark.parametrize(
    "filename, check_encoding",
    (
        # This file doesn't have any strictly unicode characters in it so it would
        # get detected as cp037 which doesn't get handled correctly on save.
        ("a_utf-8.txt", "utf-8"),
        # This file has a unicode only character as well as the previous text
        ("b_utf-8.txt", "utf-8"),
    ),
)
def test_workbox_mixin_open_file(filename, check_encoding):
    """Test how preditor handles text encoding of varous files.

    To test a specific case, add a new .txt file next to this file and add it to
    the parametrize decorator specifying the encoding that should be detected
    and decoded. Use a comment to explain what this file is testing.
    """
    filename = this_dir / filename
    encoding, text = WorkboxMixin.__open_file__(filename)
    check_bytes = filename.open("rb").read()
    check_text = check_bytes.decode(check_encoding)

    assert encoding == check_encoding
    assert text == check_text
