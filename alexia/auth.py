import re
from typing import Optional, List
from bs4 import BeautifulSoup
import requests

from alexia.config import (
    DEFAULT_USER_AGENT,
    build_login_url,
    build_ws_url,
)
from alexia.models import AuthSession, RoleInfo

DEFAULT_LOGIN_URL = build_login_url()
DEFAULT_BASE_WS = build_ws_url()


class AlexiaAuth:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        login_url: Optional[str] = None,
        base_ws: Optional[str] = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.session = session or requests.Session()
        self.login_url = login_url or build_login_url()
        self.base_ws = base_ws or build_ws_url()
        self.user_agent = user_agent

        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Referer": self.login_url,
        })

    def extract_token_from_html(self, html: str) -> str:
        # Try bs4 first
        soup = BeautifulSoup(html, "html.parser")
        token_input = soup.find("input", {"id": "Token"}) or soup.find("input", {"name": "Token"})
        if token_input and token_input.get("value"):
            return str(token_input.get("value")).strip()

        # Regex fallback
        match = re.search(r'id=["\']Token["\']\s+value=["\']([^"\']+)["\']', html)
        if not match:
            match = re.search(r'value=["\']([^"\']+)["\']\s+id=["\']Token["\']', html)
        if match:
            return match.group(1).strip()

        raise RuntimeError("No se pudo localizar el token de login en la página de Alexia.")

    def login(self, usuario: str, contrasena: str, role_id: Optional[str] = None) -> AuthSession:
        """
        Executes the 4-step authentication flow against Alexia WSLogOn.asmx.
        """
        # Step 1: Get initial login page and extract UUID token
        resp = self.session.get(self.login_url)
        resp.raise_for_status()
        token = self.extract_token_from_html(resp.text)

        # Step 2: Validate credentials
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Referer": self.login_url,
            "X-Requested-With": "XMLHttpRequest",
        }
        val_resp = self.session.post(
            f"{self.base_ws}/Validar",
            json={"token": token, "nickname": usuario, "password": contrasena},
            headers=headers,
        )
        val_resp.raise_for_status()
        val_data = val_resp.json()
        err_msg = val_data.get("d", "")
        if err_msg:
            raise ValueError(f"Fallo en credenciales de Alexia: {err_msg}")

        # Step 3: Get user roles
        roles_resp = self.session.post(
            f"{self.base_ws}/GetRoles",
            json={"token": token},
            headers=headers,
        )
        roles_resp.raise_for_status()
        roles_payload = roles_resp.json().get("d", {})

        if roles_payload.get("Error"):
            raise RuntimeError(f"Error al obtener roles: {roles_payload['Error']}")

        raw_roles = roles_payload.get("OK", [])
        if not raw_roles:
            raise RuntimeError("El usuario no tiene roles activos en Everest School.")

        roles_list: List[RoleInfo] = []
        for r in raw_roles:
            r_id = str(r.get("Identificador", ""))
            r_name = str(r.get("Nombre", ""))
            roles_list.append(RoleInfo(id=r_id, nombre=r_name, raw=r))

        # Select role: specified or default to the first
        if role_id:
            matching = [r for r in roles_list if r.id == role_id]
            if not matching:
                raise ValueError(f"Rol {role_id} no encontrado en la lista de roles del usuario.")
            selected_rol = matching[0].id
        else:
            selected_rol = roles_list[0].id

        # Step 4: Validate role and finalize session
        rol_resp = self.session.post(
            f"{self.base_ws}/ValidarRol",
            json={"token": token, "idRol": selected_rol, "evaluarMultifactor": False},
            headers=headers,
        )
        rol_resp.raise_for_status()
        res_final = rol_resp.json().get("d", {})

        if not res_final.get("OK"):
            error_reason = res_final.get("Error") or "Validación de rol rechazada."
            raise RuntimeError(f"No se pudo validar el rol del usuario: {error_reason}")

        ruta_home = res_final.get("RutaHome")

        all_cookies = {c.name: c.value for c in self.session.cookies}
        session_obj = AuthSession(
            user=usuario,
            token=token,
            rol=selected_rol,
            roles=roles_list,
            ruta_home=ruta_home,
            cookies=all_cookies,
        )

        return session_obj
