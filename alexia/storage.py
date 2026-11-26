import json
import os
from pathlib import Path
from typing import Optional

from alexia.models import AuthSession

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "alexia"
SESSION_FILENAME = "session.json"


def get_config_dir() -> Path:
    env_dir = os.environ.get("ALEXIA_CONFIG_DIR")
    if env_dir:
        config_dir = Path(env_dir)
    else:
        config_dir = DEFAULT_CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_session_file() -> Path:
    return get_config_dir() / SESSION_FILENAME


def load_session() -> Optional[AuthSession]:
    session_file = get_session_file()
    if not session_file.is_file():
        return None
    try:
        content = session_file.read_text(encoding="utf-8")
        data = json.loads(content)
        return AuthSession.model_validate(data)
    except Exception:
        return None


def save_session(session: AuthSession) -> Path:
    session_file = get_session_file()
    payload = session.model_dump()
    session_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        session_file.chmod(0o600)
    except Exception:
        pass
    return session_file


def clear_session() -> bool:
    session_file = get_session_file()
    if session_file.is_file():
        session_file.unlink()
        return True
    return False
