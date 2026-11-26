import os
from alexia.config import (
    build_login_url,
    get_base_url,
    get_env_key,
    get_centro_educ,
    get_default_user,
    get_default_password,
)


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("ALEXIA_BASE_URL", raising=False)
    monkeypatch.delenv("ALEXIA_ENV_KEY", raising=False)
    monkeypatch.delenv("ALEXIA_CENTRO_EDUC", raising=False)
    monkeypatch.delenv("ALEXIA_USER", raising=False)
    monkeypatch.delenv("ALEXIA_PASS", raising=False)

    assert get_base_url() == "https://web2.alexiaedu.com"
    assert get_env_key() == "lkrP2d/Xkmc="
    assert get_centro_educ() == "gILvORwYbO0="
    assert get_default_user() is None
    assert get_default_password() is None

    url = build_login_url()
    assert "https://web2.alexiaedu.com/ACWeb/LogOn.aspx?" in url
    assert "key=lkrP2d%2FXkmc%3D" in url
    assert "keyc=gILvORwYbO0%3D" in url


def test_config_overrides(monkeypatch):
    monkeypatch.setenv("ALEXIA_BASE_URL", "https://colegio.test")
    monkeypatch.setenv("ALEXIA_ENV_KEY", "custom_key")
    monkeypatch.setenv("ALEXIA_CENTRO_EDUC", "custom_centro")
    monkeypatch.setenv("ALEXIA_USER", "usuario_env")
    monkeypatch.setenv("ALEXIA_PASS", "pass_env")

    assert get_base_url() == "https://colegio.test"
    assert get_env_key() == "custom_key"
    assert get_centro_educ() == "custom_centro"
    assert get_default_user() == "usuario_env"
    assert get_default_password() == "pass_env"

    url = build_login_url()
    assert url == "https://colegio.test/ACWeb/LogOn.aspx?key=custom_key&keyc=custom_centro"
