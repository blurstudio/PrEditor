import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def shared_prefs(tmp_path_factory):
    """All tests use this prefs dir instead of the user.

    Safety to prevent possible overwriting of a user's prefs.
    """
    path = tmp_path_factory.mktemp("_shared_prefs")
    os.environ["PREDITOR_PREF_PATH"] = str(path)
    return path


@pytest.fixture()
def pref_root(tmp_path):
    """A per-test user prefs folder."""
    path = tmp_path / "_prefs"
    path.mkdir()
    os.environ["PREDITOR_PREF_PATH"] = str(path)
    return path
