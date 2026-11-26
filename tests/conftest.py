import pytest


@pytest.fixture(autouse=True)
def isolate_config_dir(tmp_path, monkeypatch):
    """Ensures no test ever reads from or writes to the real ~/.config/alexia/ directory."""
    test_config = tmp_path / "alexia_test_config"
    test_config.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ALEXIA_CONFIG_DIR", str(test_config))
