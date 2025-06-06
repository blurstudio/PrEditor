import os
from pathlib import Path

import preditor.prefs


def test_auto_fixture(tmp_path_factory):
    """Tests that the autouse fixture `shared_prefs` is applied by default."""
    path = os.environ["PREDITOR_PREF_PATH"]
    assert isinstance(path, str)
    # The fixture always adds a digit to account for multiple uses per test.
    # This is a session scoped test so it should always be zero
    assert os.path.basename(path) == "_shared_prefs0"

    # Make sure its using the pytest dir not the user folder
    pytest_root = tmp_path_factory.getbasetemp()
    assert pytest_root in Path(path).parents

    # Verify that preditor actually uses the env var.
    prefs_path = preditor.prefs.prefs_path()
    assert prefs_path == path


def test_pref_root(pref_root, tmp_path):
    """Test that if the `pref_root` fixture is used it generates a per-test pref."""
    path = os.environ["PREDITOR_PREF_PATH"]
    assert isinstance(path, str)

    # The parent folder takes care of unique names so no the _prefs folder is
    # not modified in this context.
    assert os.path.basename(path) == "_prefs"

    # Make sure its using the test dir not the user folder
    assert os.path.normpath(path).startswith(str(tmp_path))

    # Verify that preditor actually uses the env var.
    prefs_path = preditor.prefs.prefs_path()
    assert prefs_path == path
