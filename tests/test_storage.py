import os
from pathlib import Path
from alexia.models import AuthSession, RoleInfo
from alexia import storage


def test_storage_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("ALEXIA_CONFIG_DIR", str(tmp_path))

    # Initial state: no session
    assert storage.load_session() is None
    assert storage.clear_session() is False

    # Create and save session
    session = AuthSession(
        user="test_parent",
        token="uuid-1234-abcd",
        rol="1001",
        roles=[RoleInfo(id="1001", nombre="Familiar / Padre")],
        ruta_home="/ACWeb/familias/home.aspx",
        cookies={".ASPXAUTH": "dummyauthcookie", "ASP.NET_SessionId": "sess123"},
    )
    saved_path = storage.save_session(session)
    assert saved_path.exists()

    # Load session
    loaded = storage.load_session()
    assert loaded is not None
    assert loaded.user == "test_parent"
    assert loaded.token == "uuid-1234-abcd"
    assert loaded.rol == "1001"
    assert loaded.is_authenticated is True
    assert loaded.cookies.get(".ASPXAUTH") == "dummyauthcookie"

    # Clear session
    assert storage.clear_session() is True
    assert storage.load_session() is None
