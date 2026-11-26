import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup

from alexia.client import AlexiaClient
from alexia.models import StudentItem


class StudentService:
    def __init__(self, client: Optional[AlexiaClient] = None):
        self.client = client or AlexiaClient()

    def _ensure_authenticated(self):
        if not self.client.is_authenticated:
            raise RuntimeError(
                "No hay una sesión activa de Alexia. Por favor, ejecuta 'alexia auth login' primero."
            )

    def list_students(self, fetch_academic: bool = True) -> List[StudentItem]:
        self._ensure_authenticated()

        home_url = f"{self.client.base_url}/ACWeb/paginas/Home/HomeMetro.aspx"
        resp = self.client.get(home_url, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        students_by_persona_key: Dict[str, StudentItem] = {}
        students_by_guid: Dict[str, StudentItem] = {}

        # 1. Parse lienzo_hijos: gives full name and GuidAlumno
        lienzo = soup.find(id="ctl00_ContenidoPagina_ctl07_cmptHijosSeg_lienzo_hijos")
        if lienzo:
            for li in lienzo.find_all("li", recursive=False):
                guid_alumno = li.get("hijo") or li.get("guid") or ""
                nombre_p = li.find("p")
                nombre_completo = nombre_p.get_text(strip=True) if nombre_p else "Alumno"

                img = li.find("img")
                foto_src = img.get("src", "") if img else ""
                foto_url = self.client.resolve_url(foto_src) if foto_src else None

                # Extract key parameter from foto_src (persona_key)
                persona_key = None
                if foto_src:
                    parsed = urlparse(foto_src)
                    qs = parse_qs(parsed.query)
                    keys = qs.get("key")
                    if keys:
                        persona_key = keys[0]

                item = StudentItem(
                    id=str(guid_alumno),
                    persona_key=persona_key,
                    nombre=nombre_completo,
                    parentesco="Hijo/a",
                    foto_url=foto_url,
                    raw={"lienzo_html": str(li)},
                )
                if guid_alumno:
                    students_by_guid[str(guid_alumno)] = item
                if persona_key:
                    students_by_persona_key[persona_key] = item

        # 2. Parse lista_users: gives parentesco (Hijo / Hija) and persona_key
        users_list = soup.find(id="ctl00_ContenidoPagina_contenido_agenda_cmptHijo_lista_users")
        if users_list:
            for li in users_list.find_all("li", class_=lambda c: c and "hijo" in c):
                onclick = li.get("onclick", "")
                persona_key_match = re.search(r"HijoClicked\s*\(\s*this\s*,\s*['\"]([^'\"]+)['\"]", onclick)
                persona_key = persona_key_match.group(1) if persona_key_match else None

                parentesco_tag = li.find("strong")
                parentesco = parentesco_tag.get_text(strip=True) if parentesco_tag else "Hijo/a"

                nombre_h3 = li.find("h3")
                nombre_corto = nombre_h3.get_text(strip=True) if nombre_h3 else ""

                if persona_key and persona_key in students_by_persona_key:
                    matched = students_by_persona_key[persona_key]
                    matched.parentesco = parentesco
                    if not matched.nombre or matched.nombre == "Alumno":
                        matched.nombre = nombre_corto
                else:
                    # Match by short name if persona_key wasn't in lienzo
                    found_match = False
                    for st in students_by_guid.values():
                        if nombre_corto and nombre_corto.lower() in st.nombre.lower():
                            st.parentesco = parentesco
                            st.persona_key = persona_key
                            found_match = True
                            break

                    if not found_match and persona_key:
                        new_item = StudentItem(
                            id=persona_key,
                            persona_key=persona_key,
                            nombre=nombre_corto or "Alumno",
                            parentesco=parentesco,
                        )
                        students_by_persona_key[persona_key] = new_item
                        students_by_guid[persona_key] = new_item

        students_list = list(students_by_guid.values())

        # 3. If academic details requested, fetch courses and active enrollments
        if fetch_academic:
            calif_url = f"{self.client.base_url}/ACWeb/WS_Data/WSHome.asmx/GetWPCalificaciones"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Referer": home_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            for student in students_list:
                if not student.id:
                    continue
                try:
                    resp_c = self.client.post(calif_url, json={"idAlumno": student.id}, headers=headers, timeout=6)
                    if resp_c.status_code == 200:
                        calif_html = resp_c.json().get("d", {}).get("calificaciones", "")
                        if calif_html:
                            soup_c = BeautifulSoup(calif_html, "html.parser")
                            cmb = soup_c.find("select", id=lambda x: x and "cmbMatricula" in x)
                            if cmb:
                                matriculas = [opt.get_text(strip=True) for opt in cmb.find_all("option") if opt.get_text(strip=True)]
                                student.matriculas = matriculas
                                if matriculas:
                                    student.curso = matriculas[0]
                except Exception:
                    pass

        return students_list
