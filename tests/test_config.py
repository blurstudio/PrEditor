import pytest

import preditor.config
import preditor.excepthooks
import preditor.stream
from preditor.config import PreditorConfig


def test_init():
    """Test the defaults of Config init."""
    cfg = PreditorConfig()
    assert cfg.name is None
    assert cfg.streams is False
    assert cfg.excepthook is False
    assert cfg.logging is False
    assert cfg.headless_callback is None
    assert cfg.parent_callback is None

    # Ensure complete coverage of update_logging by setting logging to False.
    cfg.logging = False
    assert cfg.logging is False


def test_disbled_by_default():
    # Complete coverage of excepthook setter not covered by monkeypatch tests
    cfg = PreditorConfig()
    cfg.excepthook = False
    assert cfg.excepthook is False

    # Complete coverage of streams setter not covered by monkeypatch tests
    cfg = PreditorConfig()
    cfg.streams = False
    assert cfg.streams is False


@pytest.fixture()
def patch_data():
    """A data structure used by monkeypatch methods to track calling."""
    return {
        "inst": {
            "called": False,
            "state": False,
        }
    }


@pytest.fixture()
def patch_inst(patch_data, monkeypatch):
    """Replaces preditor.instance with a method that tests can control.

    Uses the dictionary provided by `patch_data`. `patch_data["inst"]["called"]`
    is set to True any time this method is called. `patch_data["inst"]["state"]`
    can be set to the value you want this method to return. This will be set if
    you pass `create=True`.
    """

    def inst(cls, create=False):
        patch_data["inst"]["called"] = True
        if create:
            patch_data["inst"]["state"] = True
        return patch_data["inst"]["state"]

    monkeypatch.setattr(PreditorConfig, "instance", classmethod(inst))
    return inst


def test_logging(monkeypatch, patch_data, patch_inst):
    """Ensure the logging api is called correctly for various changes."""

    class PatchLoggingConfig:
        called = False

        def __init__(self, core_name):
            self.core_name = core_name

        @classmethod
        def load(cls):
            cls.called = True

        @classmethod
        def reset(cls):
            cls.called = False

    monkeypatch.setattr(preditor.logging_config, "LoggingConfig", PatchLoggingConfig)
    assert not patch_data["inst"]["called"]

    # Logging is not installed by default
    cfg = PreditorConfig()
    assert cfg.logging is False
    assert not PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Test directly calling update_logging with logging disabled does nothing
    cfg.update_logging()
    assert not PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Test enabling logging without setting name calls update_logging, but
    # doesn't actually install logging
    cfg.logging = True
    assert not PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Setting name with logging enabled will install logging using update_logging
    assert cfg.name is None
    assert cfg.logging is True
    cfg.name = "pytest"
    assert cfg.name == "pytest"
    assert cfg.logging is True
    assert PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Attempt to set name to its current value does not install logging
    cfg.name = "pytest"
    assert cfg.name == "pytest"
    assert not PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Changing the name forces logging updates if enabled
    cfg.name = "pytest_1"
    assert cfg.name == "pytest_1"
    assert PatchLoggingConfig.called
    PatchLoggingConfig.reset()

    # Once the instance has been made changing the name does nothing
    cfg.instance(create=True)
    assert cfg.name == "pytest_1"
    cfg.name = "pytest_2"
    assert cfg.name == "pytest_1"
    assert not PatchLoggingConfig.called
    PatchLoggingConfig.reset()


def test_excepthook(monkeypatch, patch_data, patch_inst):
    class PatchExcepthookClass:
        called = False
        installed = False

        def __init__(self, base_excepthook=None):
            self.base_excepthook = base_excepthook

        def __call__(self, *exc_info):
            type(self).called = True

        @classmethod
        def install(cls, force=False):
            cls.installed = True

        @classmethod
        def reset(cls):
            cls.called = False
            cls.installed = False

    monkeypatch.setattr(
        preditor.excepthooks, "PreditorExceptHook", PatchExcepthookClass
    )

    # Test enabling after init
    cfg = PreditorConfig()
    assert cfg.excepthook is False
    assert PatchExcepthookClass.installed is False

    # The value can be updated as long as instance is False.
    assert not patch_data["inst"]["state"]
    cfg.excepthook = True
    assert cfg.excepthook is True
    assert PatchExcepthookClass.installed is True
    PatchExcepthookClass.reset()

    # However calling it a second time doesn't allow changing. This method installs
    # an chaining except hook that calls the previous one. If the user wants to
    # add their own except hook after the fact they should do it manually.
    cfg.excepthook = False
    assert cfg.excepthook is True
    assert PatchExcepthookClass.installed is False

    # Install the excepthook
    cfg = PreditorConfig()
    cfg.excepthook = True

    # Can not be disabled after enabled
    assert not patch_data["inst"]["state"]
    cfg.excepthook = False
    assert cfg.excepthook is True

    # Once the instance is created, changing excepthook is not allowed
    cfg = PreditorConfig()
    assert cfg.excepthook is False
    cfg.instance(create=True)
    assert patch_data["inst"]["state"]
    cfg.excepthook = True
    assert cfg.excepthook is False


def test_streams(monkeypatch, patch_data, patch_inst):
    def install_to_std():
        patch_data["install_to_std"] = True

    def reset_stream_install():
        patch_data["install_to_std"] = False

    monkeypatch.setattr(preditor.stream, "install_to_std", install_to_std)
    reset_stream_install()

    # Stream is not installed by default
    cfg = PreditorConfig()
    assert not cfg.streams
    assert not patch_data["install_to_std"]
    # And doesn't install if set to False
    cfg.streams = False
    assert not cfg.streams
    assert not patch_data["install_to_std"]

    # Setting to True installs the stream
    cfg.streams = True
    assert cfg.streams
    assert patch_data["install_to_std"]
    reset_stream_install()

    # Streams are not re-installed after enabled
    cfg.streams = True
    assert cfg.streams
    assert not patch_data["install_to_std"]
    # And not uninstalled after being enabled
    cfg.streams = False
    assert cfg.streams
    assert not patch_data["install_to_std"]


@pytest.mark.parametrize("name", ("headless_callback", "parent_callback"))
def test_callbacks(name, patch_data, patch_inst):
    def callback_1():
        pass

    def callback_2():
        pass

    cfg = PreditorConfig()
    assert getattr(cfg, name) is None

    # We can edit the callback
    setattr(cfg, name, callback_1)
    assert getattr(cfg, name) is callback_1
    # We can edit the callback multiple times
    setattr(cfg, name, callback_2)
    assert getattr(cfg, name) is callback_2
    # Once the instance is created, we can no longer edit the callback
    cfg.instance(create=True)
    assert patch_data["inst"]["state"]
    setattr(cfg, name, callback_1)
    assert getattr(cfg, name) is callback_2
