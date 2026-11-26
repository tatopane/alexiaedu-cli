from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse
import requests

from alexia.config import DEFAULT_USER_AGENT, get_base_url
from alexia.models import AuthSession
from alexia import storage

BASE_URL = get_base_url()


class AlexiaClient:
    def __init__(
        self,
        session_obj: Optional[AuthSession] = None,
        base_url: Optional[str] = None,
        auto_load: bool = True,
    ):
        self.base_url = (base_url or get_base_url()).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
        })
        self.session_obj: Optional[AuthSession] = session_obj

        if self.session_obj is None and auto_load:
            self.session_obj = storage.load_session()

        if self.session_obj and self.session_obj.cookies:
            domain = urlparse(self.base_url).hostname
            for k, v in self.session_obj.cookies.items():
                self.session.cookies.set(k, v, domain=domain, path="/")

    @property
    def is_authenticated(self) -> bool:
        if not self.session_obj:
            return False
        return self.session_obj.is_authenticated

    def _sync_cookies(self):
        if self.session_obj:
            current_cookies = {c.name: c.value for c in self.session.cookies}
            self.session_obj.cookies.update(current_cookies)
            storage.save_session(self.session_obj)

    def resolve_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        if not path_or_url.startswith("/"):
            path_or_url = f"/{path_or_url}"
        return f"{self.base_url}{path_or_url}"

    def get(self, url: str, **kwargs) -> requests.Response:
        full_url = self.resolve_url(url)
        resp = self.session.get(full_url, **kwargs)
        self._sync_cookies()
        return resp

    def post(self, url: str, **kwargs) -> requests.Response:
        full_url = self.resolve_url(url)
        resp = self.session.post(full_url, **kwargs)
        self._sync_cookies()
        return resp

    def check_status(self) -> Dict[str, Any]:
        """
        Verifies if the current stored session is valid and active.
        """
        if not self.session_obj:
            return {"authenticated": False, "reason": "No hay sesión activa guardada."}

        # Check if cookie contains .ASPXAUTH
        if not self.session_obj.is_authenticated:
            return {
                "authenticated": False,
                "user": self.session_obj.user,
                "reason": "La sesión no tiene la cookie .ASPXAUTH.",
            }

        # Optionally test against home route if available
        test_url = self.session_obj.ruta_home or "/ACWeb/comunicaciones"
        try:
            resp = self.get(test_url, allow_redirects=False, timeout=10)
            if resp.status_code in (200, 302):
                redirect_loc = resp.headers.get("Location", "")
                if "LogOn.aspx" in redirect_loc:
                    return {
                        "authenticated": False,
                        "user": self.session_obj.user,
                        "reason": "La sesión ha expirado en el servidor (redirige a LogOn).",
                    }
                return {
                    "authenticated": True,
                    "user": self.session_obj.user,
                    "rol": self.session_obj.rol,
                    "ruta_home": self.session_obj.ruta_home,
                    "created_at": self.session_obj.created_at,
                }
            return {
                "authenticated": False,
                "user": self.session_obj.user,
                "reason": f"Código de estado inesperado al verificar sesión: {resp.status_code}",
            }
        except Exception as e:
            # If network error or unreachable, report status with warning
            return {
                "authenticated": True,
                "user": self.session_obj.user,
                "rol": self.session_obj.rol,
                "warning": f"No se pudo verificar activamente con el servidor: {e}",
            }
