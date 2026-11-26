import pytest
import responses
from alexia.auth import AlexiaAuth, DEFAULT_LOGIN_URL, DEFAULT_BASE_WS


def test_extract_token_from_html():
    auth = AlexiaAuth()
    html_standard = '<html><body><input type="hidden" name="Token" id="Token" value="12345-uuid-67890" /></body></html>'
    assert auth.extract_token_from_html(html_standard) == "12345-uuid-67890"

    html_inverted = '<html><body><input value="invert-uuid-val" id="Token" /></body></html>'
    assert auth.extract_token_from_html(html_inverted) == "invert-uuid-val"

    with pytest.raises(RuntimeError):
        auth.extract_token_from_html("<html><body>No token here</body></html>")


@responses.activate
def test_login_flow_success():
    login_html = '<html><input type="hidden" id="Token" value="abc-token-uuid" /></html>'
    responses.add(responses.GET, DEFAULT_LOGIN_URL, body=login_html, status=200)

    # Validar
    responses.add(
        responses.POST,
        f"{DEFAULT_BASE_WS}/Validar",
        json={"d": ""},
        status=200,
    )

    # GetRoles
    responses.add(
        responses.POST,
        f"{DEFAULT_BASE_WS}/GetRoles",
        json={
            "d": {
                "OK": [
                    {"Identificador": "ROLE_PADRE", "Nombre": "Familiar / Padre"}
                ],
                "multifactor": False,
                "Ruta": None,
            }
        },
        status=200,
    )

    # ValidarRol
    responses.add(
        responses.POST,
        f"{DEFAULT_BASE_WS}/ValidarRol",
        json={"d": {"OK": True, "RutaHome": "/ACWeb/home.aspx"}},
        headers={"Set-Cookie": ".ASPXAUTH=securetoken123; path=/"},
        status=200,
    )

    auth = AlexiaAuth()
    session = auth.login("usuario_test", "password_test")

    assert session.user == "usuario_test"
    assert session.token == "abc-token-uuid"
    assert session.rol == "ROLE_PADRE"
    assert session.ruta_home == "/ACWeb/home.aspx"
    assert session.is_authenticated is True
    assert ".ASPXAUTH" in session.cookies


@responses.activate
def test_login_invalid_credentials():
    login_html = '<html><input type="hidden" id="Token" value="abc-token-uuid" /></html>'
    responses.add(responses.GET, DEFAULT_LOGIN_URL, body=login_html, status=200)

    # Validar returns error message
    responses.add(
        responses.POST,
        f"{DEFAULT_BASE_WS}/Validar",
        json={"d": "Usuario o contraseña incorrectos."},
        status=200,
    )

    auth = AlexiaAuth()
    with pytest.raises(ValueError, match="Usuario o contraseña incorrectos"):
        auth.login("wrong_user", "wrong_pass")
