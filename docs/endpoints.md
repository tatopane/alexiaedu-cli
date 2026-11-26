# 📡 Especificación Técnica de Endpoints de Alexia Familias

Documentación técnica detallada de la API inversa de **Alexia Familias** (`web2.alexiaedu.com`) obtenida durante el desarrollo de `alexia-cli`, con foco en la implementación de **Everest School**.

---

## 🏛️ 1. Parámetros Institucionales (Everest School)

* **URL Base:** `https://web2.alexiaedu.com`
* **Parámetros Institucionales:**
  * `key`: `lkrP2d/Xkmc=` (URL encoded: `lkrP2d%2FXkmc%3D`) - Identificador del entorno
  * `keyc`: `gILvORwYbO0=` (URL encoded: `gILvORwYbO0%3D`) - Clave del colegio (Everest School)
  * `LastIdInstitucion` / `numInstitucionLogOn`: `1752` - ID numérico de Everest School

---

## 🔐 2. Módulo de Autenticación y Sesión

Alexia no expone una API REST tradicional, sino WebServices ASP.NET (`.asmx`) que serializan llamadas AJAX en formato JSON (`application/json; charset=utf-8`) sobre la sesión ASP.NET.

### 2.1 Obtención del Token de Inicio de Sesión
* **Método:** `GET`
* **Endpoint:** `/ACWeb/LogOn.aspx?key=lkrP2d%2FXkmc%3D&keyc=gILvORwYbO0%3D`
* **Headers:**
  ```http
  User-Agent: Mozilla/5.0 ...
  ```
* **Respuesta:**
  - Código: `200 OK`
  - Cookies emitidas: `AC_SessionId`, `LogOnToken`
  - Extracción en HTML: `<input type="hidden" name="Token" id="Token" value="<UUID>" />`

---

### 2.2 Validación de Credenciales (`Validar`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSLogOn.asmx/Validar`
* **Headers:**
  ```http
  Content-Type: application/json; charset=utf-8
  Referer: https://web2.alexiaedu.com/ACWeb/LogOn.aspx?key=...
  X-Requested-With: XMLHttpRequest
  ```
* **Payload:**
  ```json
  {
    "token": "<UUID_TOKEN>",
    "nickname": "<USUARIO>",
    "password": "<PASSWORD>"
  }
  ```
  > [!NOTE]
  > El servicio web de ASP.NET requiere el parámetro `nickname` (no `usuario`).
* **Respuesta Exitosa:**
  ```json
  {
    "d": ""
  }
  ```
* **Respuesta Errónea:**
  ```json
  {
    "d": "Usuario o contraseña incorrectos."
  }
  ```

---

### 2.3 Consulta de Roles de Usuario (`GetRoles`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSLogOn.asmx/GetRoles`
* **Headers:** `Content-Type: application/json; charset=utf-8`
* **Payload:**
  ```json
  {
    "token": "<UUID_TOKEN>"
  }
  ```
* **Respuesta:**
  ```json
  {
    "d": {
      "OK": [
        {
          "Identificador": "<GUID_ROL>"
        }
      ],
      "multifactor": false,
      "Ruta": null
    }
  }
  ```

---

### 2.4 Confirmación y Selección de Rol (`ValidarRol`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSLogOn.asmx/ValidarRol`
* **Headers:** `Content-Type: application/json; charset=utf-8`
* **Payload:**
  ```json
  {
    "token": "<UUID_TOKEN>",
    "idRol": "<GUID_ROL>",
    "evaluarMultifactor": false
  }
  ```
  > [!NOTE]
  > Requiere los nombres exactos `idRol` y `evaluarMultifactor`.
* **Respuesta:**
  ```json
  {
    "d": {
      "OK": true,
      "OKCuenta": true,
      "RutaHome": "/ACWeb/paginas/Home/HomeMetro.aspx"
    }
  }
  ```
* **Cookies Consolidadas de Sesión:**
  - `.ASPXAUTH`: Cookie de autenticación persistente
  - `datosUsr`: Información de sesión serializada (`{"locale":"es","rol":"Padre"}`)
  - `LastIdInstitucion`: `1752`
  - `InicioSesion`: Marca de tiempo

---

## 📬 3. Notificaciones y Comunicados (`WSHome.asmx` / `WSComunicados.asmx`)

### 3.1 Listado de Comunicados de la Home (`GetWPDetalleDTO`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSHome.asmx/GetWPDetalleDTO`
* **Headers:**
  ```http
  Content-Type: application/json; charset=utf-8
  Referer: https://web2.alexiaedu.com/ACWeb/paginas/Home/HomeMetro.aspx
  X-Requested-With: XMLHttpRequest
  ```
* **Payload:**
  ```json
  {
    "idPastilla": "comunicados",
    "esHome": true,
    "esHomeProgDidactica": false
  }
  ```
* **Respuesta:**
  ```json
  {
    "d": {
      "__type": "CospaAgilmic.NS.Negocio.DTO.WebParts.ListadoWPDTO",
      "Items": [
        {
          "Id": "00000000-0000-0000-0000-000000000001",
          "Title": "Circular Informativa de Ejemplo",
          "Subtitle": "de: Colegio de Prueba",
          "RightSubtitle": "26/11/2026",
          "OnClick": {
            "Url": "~/paginas/Comunicacion/Comunicado.aspx?GuidComunicadoOrigen=00000000-0000-0000-0000-000000000001&TipoComunicado=N&AccionComunicado=1&master=2"
          },
          "Data": {
            "Guid": "00000000-0000-0000-0000-000000000001",
            "Titulo": "Circular Informativa de Ejemplo",
            "IsLeido": false
          }
        }
      ]
    }
  }
  ```

---

### 3.2 Carga de Contexto del Comunicado (`Comunicado.aspx`)
* **Método:** `GET`
* **Endpoint:** `/ACWeb/paginas/Comunicacion/Comunicado.aspx?GuidComunicadoOrigen={GUID}&TipoComunicado=N&AccionComunicado=1&master=2`
* **Headers:**
  ```http
  Referer: https://web2.alexiaedu.com/ACWeb/paginas/Home/HomeMetro.aspx
  ```
* **Propósito:** Prepara el estado y variables de sesión en el servidor para permitir la consulta AJAX inmediata de su contenido.

---

### 3.3 Detalle del Comunicado y Adjuntos (`GetDatosPaginaComunicado`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSComunicados.asmx/GetDatosPaginaComunicado`
* **Headers:**
  ```http
  Content-Type: application/json; charset=utf-8
  Referer: https://web2.alexiaedu.com/ACWeb/paginas/Comunicacion/Comunicado.aspx?...
  X-Requested-With: XMLHttpRequest
  ```
* **Payload:** `{}`
* **Respuesta:**
  ```json
  {
    "d": {
      "Asunto_1": "Circular Informativa de Ejemplo",
      "Mensaje_1": "<p><span>Adjuntamos circular en formato PDF.</span></p>",
      "FechaPublicacion": "2026-11-26",
      "HoraPublicacion": "16:00",
      "NombreEmisor": "Colegio de Prueba",
      "AdjuntosExistentes": [
        {
          "Id": "archivo_ejemplo_123.pdf",
          "Nombre": "CircularInformativa.pdf",
          "Tamanio": 512000
        }
      ]
    }
  }
  ```

---

### 3.4 Descarga de Adjuntos Autenticados (`ControladorRepositorio.ashx`)
* **Método:** `GET`
* **Endpoint:** `/ACWeb/Controladores/ControladorRepositorio.ashx?tipo=6&nombre={ADJUNTO_ID}`
* **Headers:** Requiere cookies de sesión (`.ASPXAUTH`).
* **Respuesta:**
  - `Content-Type: application/octet-stream` (o PDF)
  - Flujo binario directo del archivo.

---

## 👨‍👩‍👧‍👦 4. Alumnos e Información Académica

### 4.1 Identificación de Alumnos / Hijos (`HomeMetro.aspx`)
* **Método:** `GET`
* **Endpoint:** `/ACWeb/paginas/Home/HomeMetro.aspx`
* **Extracción HTML:**
  1. `#ctl00_ContenidoPagina_ctl07_cmptHijosSeg_lienzo_hijos li`:
     - Atributo `hijo="<GuidAlumno>"` (ej. `00000000-0000-0000-0000-000000000001`)
     - Nombre completo en `<p>`
     - URL de foto con parámetro `key="<KeyPersona>"`
  2. `#ctl00_ContenidoPagina_contenido_agenda_cmptHijo_lista_users li.hijo`:
     - Parentesco (`Hijo` / `Hija`) en `<strong>`
     - Nombre corto en `<h3>`

---

### 4.2 Matrícula, Cursos y Evaluaciones (`GetWPCalificaciones`)
* **Método:** `POST`
* **Endpoint:** `/ACWeb/WS_Data/WSHome.asmx/GetWPCalificaciones`
* **Payload:**
  ```json
  {
    "idAlumno": "<GuidAlumno>"
  }
  ```
* **Respuesta:**
  - `d.calificaciones`: Fragmento HTML con selects de configuración:
    - `<select id="ctl00_cmbMatricula">`: Opciones con el curso principal (ej. *Tercero de Primaria B*, *Castor verde*) y actividades/servicios asociados (*Comedor Mensual*, *Piano*, *Fútbol*).
    - `<select id="ctl00_cmbEvaluacion">`: Opciones de trimestres y evaluaciones (*1TRIM*, *2TRIM*, *FINAL*).

---

### 4.3 Fotografía Oficial (`ControladorFotografias.ashx`)
* **Método:** `GET`
* **Endpoint:** `/ACWeb/controladores/ControladorFotografias.ashx?tipo=2&key={KeyPersona}&formato=0&maxWidth=100&maxHeigth=100`
* **Respuesta:** Imagen binaria (PNG/JPEG/SVG).

---

## 📄 5. Descarga de Circulares Públicas sin Login (`Repositorio.aspx`)

Utilizado en los enlaces que llegan por email externo a las familias.

* **URL:** `/ACWeb/paginas/publicas/Repositorio.aspx?token={TOKEN}`
* **Flujo en 2 pasos:**
  1. `GET` a la URL con token para capturar los valores ocultos de ASP.NET (`__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION`).
  2. `POST` a la misma URL con los campos del formulario más el postback:
     ```http
     __EVENTTARGET=devolver_fichero
     __EVENTARGUMENT=
     __VIEWSTATE=...
     __VIEWSTATEGENERATOR=...
     __EVENTVALIDATION=...
     ```
* **Respuesta:**
  - Código: `200 OK`
  - Header: `Content-Disposition: attachment; filename="..."`
  - Flujo binario del archivo (típicamente PDF).
