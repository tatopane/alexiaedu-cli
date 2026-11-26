# 🤖 AGENTS.md - Developer & AI Agent Guidelines for `alexiaedu-cli`

This document provides context, architectural design, technical quirks, and development guidelines for AI agents (and human contributors) working on **`alexiaedu-cli`**.

---

## 🎯 1. Project Purpose & High-Level Architecture

`alexiaedu-cli` is a lightweight, headless command-line client and Python library for **Alexia Familias** (`web2.alexiaedu.com`), with native pre-configuration for **Everest School**.

### Core Philosophy
* **Zero Headless Browsers:** No Playwright, Puppeteer, or Selenium. All operations use direct HTTP requests against Alexia's native ASP.NET ASMX WebServices (`application/json; charset=utf-8`) and ASHX handlers.
* **Persistent Session:** Auth cookies (`.ASPXAUTH`, `AC_SessionId`, `datosUsr`, etc.) are saved in `~/.config/alexia/session.json` with `0600` file permissions.
* **Dual Operation Mode:** Interactive terminal prompts for manual usage, and non-interactive environment/`.env` variable support for bots, automation agents, or cron jobs.

---

## 📁 2. Codebase Structure

```plaintext
alexiaedu-cli/
├── alexia/
│   ├── __init__.py
│   ├── config.py           # Environment loading (.env), default keys, URL helpers
│   ├── models.py           # Pydantic models (AuthSession, NotificationItem, StudentItem, etc.)
│   ├── storage.py          # Session persistence (~/.config/alexia/session.json)
│   ├── auth.py             # 4-step login flow against WSLogOn.asmx
│   ├── client.py           # requests.Session wrapper with cookie syncing & base URL resolution
│   ├── repository.py       # Public circular download via Repositorio.aspx postback
│   ├── notifications.py    # Announcement listing & detail fetching via ASMX services
│   ├── students.py         # Student profile & academic enrollment parsing
│   └── cli.py              # Typer CLI commands formatted with Rich
├── docs/
│   └── endpoints.md        # Reverse-engineered API endpoint reference
├── tests/
│   ├── conftest.py         # Config isolation fixture (sets ALEXIA_CONFIG_DIR to tmp_path)
│   ├── test_auth.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_notifications.py
│   ├── test_repository.py
│   ├── test_storage.py
│   └── test_students.py
├── .env.sample             # Environment variable template
├── pyproject.toml          # Hatchling build configuration & dependencies
└── README.md               # User-facing documentation
```

---

## ⚠️ 3. Critical Technical Quirks & ASP.NET Peculiarities

When modifying or extending the API calls, pay strict attention to the following reverse-engineered Alexia traits:

1. **Parameter Naming in `WSLogOn.asmx`:**
   * `/Validar`: Must use `nickname` (e.g. `{"token": "...", "nickname": "...", "password": "..."}`). Using `usuario` will trigger a 500 Deserialization Error.
   * `/ValidarRol`: Must use `idRol` and `evaluarMultifactor: false` (e.g. `{"token": "...", "idRol": "...", "evaluarMultifactor": false}`). Using `rol` or `forzar` will fail.
2. **ASMX Headers:**
   * ASMX JSON endpoints require `Content-Type: application/json; charset=utf-8` and `X-Requested-With: XMLHttpRequest`.
3. **Cookie Scope:**
   * Cookies returned by Alexia (such as `.ASPXAUTH`) must be stored and re-applied with domain `web2.alexiaedu.com` and path `/` across all session requests.
4. **Context Page Loading for Comunicados:**
   * Before querying `/ACWeb/WS_Data/WSComunicados.asmx/GetDatosPaginaComunicado`, the client must issue a `GET` to `/ACWeb/paginas/Comunicacion/Comunicado.aspx?GuidComunicadoOrigen={id}&TipoComunicado=N&AccionComunicado=1&master=2` with `Referer: .../HomeMetro.aspx` to initialize server-side ASP.NET session state.
5. **Attachment Downloads:**
   * Attachments for authenticated communications are served via `/ACWeb/Controladores/ControladorRepositorio.ashx?tipo=6&nombre={attachment_id}` using an authenticated session.
   * Public email circulars are served via `/ACWeb/paginas/publicas/Repositorio.aspx?token={token}` using form postback `__EVENTTARGET = "devolver_fichero"`.

---

## 🔒 4. Privacy, Security & Open Source Rules

* **NEVER Commit Real Credentials or Tokens:** `.env` and `*.session.json` are strictly ignored by `.gitignore`. Never hardcode user passwords, real `.ASPXAUTH` cookies, or tokens in source code or docs.
* **NEVER Commit Real Family Data:**
  * When writing tests or documentation examples, **ALWAYS use generic placeholder names** (e.g. `Lucas García`, `Sofía García`, `Colegio de Prueba`, `00000000-0000-0000-0000-000000000001`).
  * Never commit real names of family members, student GUIDs, or personal communication content.
* **Institutional Keys:**
  * The default Everest School keys in `alexia/config.py` (`lkrP2d/Xkmc=`, `gILvORwYbO0=`, institution `1752`) are public identifiers embedded in standard login URLs and are safe to keep as project defaults.

---

## 🧪 5. Testing & Verification Guidelines

* **Test Framework:** `pytest` with `responses` for mocking HTTP traffic.
* **Config Isolation:** `tests/conftest.py` contains an autouse fixture that redirects `ALEXIA_CONFIG_DIR` to a temporary directory. Any new test that invokes `AlexiaClient` or `storage` will not touch the host's actual `~/.config/alexia/session.json`.
* **Running the Test Suite:**
  ```bash
  source .venv/bin/activate
  pytest -v
  ```
  All tests must pass 100% without network access.

---

## ⌨️ 6. Useful Local Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in editable mode with development dependencies
uv pip install -e ".[dev]"

# Execute CLI commands
alexia auth status
alexia notif list
alexia students list
```
