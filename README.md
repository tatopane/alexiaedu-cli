# 🎓 AlexiaEdu CLI (`alexiaedu-cli` / `alexia`)

Cliente de línea de comandos (CLI) rápido, ligero y modular para **Alexia Familias** (`web2.alexiaedu.com`), optimizado específicamente para **Everest School**.

Permite autenticarse mediante los servicios web nativos de Alexia (sin navegadores headless pesados), mantener la sesión activa mediante persistencia de cookies, descargar circulares y documentos enlazados en emails sin necesidad de login, y consultar notificaciones institucionales.

---

## ⚡ Características Principales

* **Autenticación Nativa y Rápida:** Flujo asíncrono en 4 pasos contra el WebService ASP.NET (`WSLogOn.asmx`), sin requerir Playwright, Puppeteer ni Selenium.
* **Persistencia de Sesión Segura:** Guarda las cookies de autenticación (`.ASPXAUTH`, `AC_SessionId`) en `~/.config/alexia/session.json` con permisos restringidos (`chmod 600`).
* **Descarga de Circulares Públicas (`Repositorio.aspx`):** Emula el postback ASP.NET (`devolver_fichero`) para descargar documentos enlazados en correos sin necesidad de iniciar sesión.
* **Módulo de Notificaciones y Comunicados:** Consulta de circulares y avisos desde la terminal con salida formateada en tablas o JSON.
* **Soporte Híbrido de Configuración (`.env`):** Funciona tanto en modo interactivo (solicitando credenciales ocultas en consola) como desatendido (usando `.env` o variables de entorno para automatizaciones, bots o cronjobs).
* **CLI Moderno:** Construido con [Typer](https://typer.tiangolo.com/) y formateado con [Rich](https://rich.readthedocs.io/).

---

## 📁 Estructura del Proyecto

```plaintext
alexiaedu-cli/
├── alexia/
│   ├── __init__.py
│   ├── config.py           # Gestión de variables de entorno (.env) y constantes
│   ├── models.py           # Modelos de datos Pydantic
│   ├── storage.py          # Gestión y persistencia en ~/.config/alexia/
│   ├── auth.py             # Flujo de login y validación de roles WSLogOn.asmx
│   ├── client.py           # Sesión HTTP requests persistente
│   ├── repository.py       # Descarga de Repositorio.aspx (circulares públicas)
│   ├── notifications.py    # Consulta y detalle de notificaciones y adjuntos
│   ├── students.py         # Consulta de alumnos y expedientes académicos
│   └── cli.py              # Comandos y subcomandos Typer / Rich
├── docs/
│   └── endpoints.md        # Especificación técnica de la API inversa de Alexia
├── tests/                  # Suite de pruebas unitarias (pytest + responses)
├── pyproject.toml          # Configuración del paquete y dependencias
├── .env.sample             # Plantilla de variables de entorno
└── README.md
```

---

## 🛠️ Requisitos e Instalación

* **Python:** `>= 3.10`
* **Herramienta recomendada:** [`uv`](https://github.com/astral-sh/uv) (o `pip`)

### 1. Clonar e instalar en entorno virtual

```bash
cd alexiaedu-cli

# Crear entorno virtual con uv
uv venv
source .venv/bin/activate

# Instalar en modo editable con herramientas de desarrollo
uv pip install -e ".[dev]"
```

*(Si utilizas `pip` estándar: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`)*

---

## ⚙️ Configuración

Puedes configurar el CLI mediante un archivo `.env` o introducir tus credenciales cuando el CLI te las pida.

### Configuración con `.env`

Copia el archivo de ejemplo y edita tus credenciales:

```bash
cp .env.sample .env
```

Contenido de `.env`:

```env
# Parámetros institucionales (por defecto Everest School)
ALEXIA_ENV_KEY=lkrP2d/Xkmc=
ALEXIA_CENTRO_EDUC=gILvORwYbO0=

# Credenciales personales (Alexia Familias)
ALEXIA_USER=mi_usuario
ALEXIA_PASS=mi_contraseña

# (Opcional)
ALEXIA_BASE_URL=https://web2.alexiaedu.com
```

> [!NOTE]
> La jerarquía de credenciales para el login es:
> 1. Argumentos explícitos de terminal (`--user`, `--password`)
> 2. Variables de entorno / archivo `.env`
> 3. Prompt interactivo seguro en terminal

---

## 📖 Guía de Uso del CLI

### 1. Autenticación (`alexia auth`)

#### Iniciar sesión
Si tienes configurado `.env`, basta con ejecutar:
```bash
alexia auth login
```
Si prefieres especificar el usuario por parámetro:
```bash
alexia auth login --user "mi_usuario"
# Te solicitará la contraseña de forma oculta y segura
```

#### Consultar estado de la sesión
Verifica si tienes una sesión guardada localmente y si el servidor de Alexia la sigue aceptando como válida:
```bash
alexia auth status
```

#### Cerrar sesión
Elimina el archivo de sesión guardado en `~/.config/alexia/session.json`:
```bash
alexia auth logout
```

---

### 2. Descarga de Circulares y Ficheros (`alexia download`)

Las circulares recibidas por email suelen apuntar a `Repositorio.aspx?token=<TOKEN>`. Puedes descargarlas directamente sin autenticarte:

```bash
# Mediante el token recibido en el correo
alexia download --token "ABC123XYZ..." -o circular_noviembre.pdf

# O pasando la URL completa directamente
alexia download --url "https://web2.alexiaedu.com/ACWeb/paginas/publicas/Repositorio.aspx?token=ABC123XYZ..."
```

---

### 3. Notificaciones y Comunicados (`alexia notif`)

*(Requiere haber iniciado sesión previamente)*

#### Listar comunicados
```bash
# Listar los últimos 10 comunicados
alexia notif list

# Filtrar solo los no leídos
alexia notif list --unread

# Salida en formato JSON (ideal para integraciones con bots o scripts)
alexia notif list --json
```

#### Ver detalle de un comunicado
```bash
# Ver contenido del comunicado por su ID
alexia notif get 1042

# Descargar automáticamente todos los archivos adjuntos
alexia notif get 1042 --download-attachments -o ./adjuntos
```

#### Marcar comunicados como leídos
```bash
# Marcar un comunicado específico por su ID
alexia notif mark-read <ID_COMUNICADO>

# Marcar todos los comunicados no leídos con más de 24 horas de antigüedad
alexia notif mark-all-read --older-than-hours 24

# Simular sin aplicar cambios en el servidor
alexia notif mark-all-read --dry-run
```

---

### 4. Alumnos e Hijos Registrados (`alexia students` / `alexia alumnos`)

*(Requiere haber iniciado sesión previamente)*

Consulta la información de los alumnos vinculados a la cuenta familiar:

```bash
# Listar alumnos con curso, parentesco y matrículas
alexia students list

# También disponible mediante el alias en español:
alexia alumnos list

# Salida en formato JSON estructurado
alexia students list --json
```

---

## 🧪 Pruebas Unitarias

El proyecto incluye tests automatizados con mocks para validar la autenticación, el almacenamiento de sesiones, la descarga de repositorios y los comandos CLI sin depender de conexión a internet:

```bash
pytest -v
```

---

## 📄 Licencia

MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
