import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote
from dotenv import load_dotenv

# Try loading .env from current directory, then from ~/.config/alexia/.env
load_dotenv()
config_env_file = Path.home() / ".config" / "alexia" / ".env"
if config_env_file.is_file():
    load_dotenv(config_env_file)

DEFAULT_BASE_URL = "https://web2.alexiaedu.com"
DEFAULT_ENV_KEY = "lkrP2d/Xkmc="
DEFAULT_CENTRO_EDUC = "gILvORwYbO0="
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def get_base_url() -> str:
    return os.environ.get("ALEXIA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_env_key() -> str:
    return os.environ.get("ALEXIA_ENV_KEY", DEFAULT_ENV_KEY)


def get_centro_educ() -> str:
    return os.environ.get("ALEXIA_CENTRO_EDUC", DEFAULT_CENTRO_EDUC)


def get_default_user() -> Optional[str]:
    return os.environ.get("ALEXIA_USER")


def get_default_password() -> Optional[str]:
    return os.environ.get("ALEXIA_PASS") or os.environ.get("ALEXIA_PASSWORD")


def build_login_url(
    base_url: Optional[str] = None,
    key: Optional[str] = None,
    keyc: Optional[str] = None,
) -> str:
    b_url = (base_url or get_base_url()).rstrip("/")
    k = key if key is not None else get_env_key()
    kc = keyc if keyc is not None else get_centro_educ()

    # Normalize by unquoting then quoting to ensure correct %2F, %3D, etc.
    encoded_key = quote(unquote(k), safe="")
    encoded_keyc = quote(unquote(kc), safe="")

    return f"{b_url}/ACWeb/LogOn.aspx?key={encoded_key}&keyc={encoded_keyc}"


def build_ws_url(base_url: Optional[str] = None) -> str:
    b_url = (base_url or get_base_url()).rstrip("/")
    return f"{b_url}/ACWeb/WS_Data/WSLogOn.asmx"
