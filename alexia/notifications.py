from pathlib import Path
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from alexia.client import AlexiaClient
from alexia.models import AttachmentItem, NotificationDetail, NotificationItem
from alexia.repository import RepositoryDownloader


class NotificationService:
    def __init__(self, client: Optional[AlexiaClient] = None):
        self.client = client or AlexiaClient()

    def _ensure_authenticated(self):
        if not self.client.is_authenticated:
            raise RuntimeError(
                "No hay una sesión activa de Alexia. Por favor, ejecuta 'alexia auth login' primero."
            )

    def list_notifications(
        self,
        unread_only: bool = False,
        limit: int = 20,
    ) -> List[NotificationItem]:
        self._ensure_authenticated()

        items: List[NotificationItem] = []

        # 1. Primary endpoint: WSHome.asmx/GetWPDetalleDTO (idPastilla: 'comunicados')
        try:
            home_metro_url = f"{self.client.base_url}/ACWeb/paginas/Home/HomeMetro.aspx"
            dto_url = f"{self.client.base_url}/ACWeb/WS_Data/WSHome.asmx/GetWPDetalleDTO"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Referer": home_metro_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            payload = {
                "idPastilla": "comunicados",
                "esHome": True,
                "esHomeProgDidactica": False,
            }
            resp = self.client.post(dto_url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("d", {})
                raw_items = data.get("Items", []) if isinstance(data, dict) else []

                for elem in raw_items:
                    item_id = str(elem.get("Id") or elem.get("Data", {}).get("Guid") or "")
                    title = str(elem.get("Title") or elem.get("Data", {}).get("Titulo") or "Sin título")
                    date_str = str(elem.get("RightSubtitle") or elem.get("RightTitle") or "")
                    sender = str(elem.get("Subtitle") or "")
                    if sender.lower().startswith("de:"):
                        sender = sender[3:].strip()

                    is_read = bool(elem.get("Data", {}).get("IsLeido", False))
                    onclick = elem.get("OnClick") or {}
                    url_comunicado = onclick.get("Url")

                    if item_id:
                        items.append(
                            NotificationItem(
                                id=item_id,
                                title=title,
                                date=date_str,
                                sender=sender,
                                read=is_read,
                                summary=None,
                                has_attachments=True,
                                raw=elem,
                            )
                        )
        except Exception:
            pass

        # 2. Secondary fallback: ASMX services
        if not items:
            candidate_services = [
                ("/ACWeb/WS_Data/WSComunicaciones.asmx/GetComunicaciones", {"soloNoLeidas": unread_only, "limite": limit}),
                ("/ACWeb/WS_Data/WSNotificaciones.asmx/GetNotificaciones", {"soloNoLeidas": unread_only}),
            ]

            for endpoint, payload in candidate_services:
                try:
                    resp = self.client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json; charset=utf-8"},
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("d", {})
                        if isinstance(data, list):
                            raw_list = data
                        elif isinstance(data, dict):
                            raw_list = data.get("OK") or data.get("Lista") or data.get("Items") or []
                        else:
                            raw_list = []

                        for elem in raw_list:
                            item_id = str(elem.get("Id") or elem.get("Identificador") or elem.get("id") or "")
                            title = str(elem.get("Titulo") or elem.get("Asunto") or elem.get("title") or "Sin título")
                            date_str = str(elem.get("Fecha") or elem.get("date") or "")
                            sender = str(elem.get("Remitente") or elem.get("Emisor") or "")
                            read = bool(elem.get("Leido") or elem.get("read", False))
                            summary = elem.get("Resumen") or elem.get("Texto")
                            has_attach = bool(elem.get("TieneAdjuntos") or elem.get("Adjuntos"))

                            if item_id:
                                items.append(
                                    NotificationItem(
                                        id=item_id,
                                        title=title,
                                        date=date_str,
                                        sender=sender,
                                        read=read,
                                        summary=summary,
                                        has_attachments=has_attach,
                                        raw=elem,
                                    )
                                )
                        if items:
                            break
                except Exception:
                    continue

        # 3. Tertiary fallback: HTML scraping
        if not items:
            page_urls = []
            if self.client.session_obj and self.client.session_obj.ruta_home:
                page_urls.append(self.client.session_obj.ruta_home)
            page_urls.extend([
                "/ACWeb/paginas/familias/Comunicaciones.aspx",
                "/ACWeb/paginas/familias/Notificaciones.aspx",
                "/ACWeb/comunicaciones",
            ])

            for page_url in page_urls:
                try:
                    resp = self.client.get(page_url, timeout=8)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")

                    rows = (
                        soup.select(".comunicacion-item")
                        or soup.select(".notificacion-item")
                        or soup.select("table.grid tr[data-id]")
                        or soup.select("table tr[id^='row_']")
                        or soup.select(".lista-notificaciones li")
                    )

                    for idx, row in enumerate(rows):
                        row_id = (
                            row.get("data-id")
                            or row.get("id")
                            or f"notif-{idx + 1}"
                        )
                        title_el = row.select_one(".titulo, .asunto, h3, h4, a")
                        title = title_el.get_text(strip=True) if title_el else "Comunicado"
                        date_el = row.select_one(".fecha, .date, time")
                        date_val = date_el.get_text(strip=True) if date_el else None
                        sender_el = row.select_one(".remitente, .emisor, .autor")
                        sender_val = sender_el.get_text(strip=True) if sender_el else None

                        is_unread = "no-leido" in row.get("class", []) or "unread" in row.get("class", [])

                        items.append(
                            NotificationItem(
                                id=str(row_id),
                                title=title,
                                date=date_val,
                                sender=sender_val,
                                read=not is_unread,
                                summary=row.get_text(strip=True)[:150],
                                raw={"html": str(row)},
                            )
                        )
                    if items:
                        break
                except Exception:
                    continue

        if unread_only:
            items = [item for item in items if not item.read]

        return items[:limit]

    def get_notification(
        self,
        notif_id: str,
        download_attachments: bool = False,
        download_dir: Optional[str] = None,
    ) -> NotificationDetail:
        self._ensure_authenticated()

        detail: Optional[NotificationDetail] = None

        # 1. Primary method: Visit Comunicado.aspx and call WSComunicados.asmx/GetDatosPaginaComunicado
        try:
            page_url = (
                f"{self.client.base_url}/ACWeb/paginas/Comunicacion/Comunicado.aspx?"
                f"GuidComunicadoOrigen={notif_id}&TipoComunicado=N&AccionComunicado=1&master=2"
            )
            home_ref = f"{self.client.base_url}/ACWeb/paginas/Home/HomeMetro.aspx"
            self.client.get(page_url, headers={"Referer": home_ref}, timeout=8)

            ws_url = f"{self.client.base_url}/ACWeb/WS_Data/WSComunicados.asmx/GetDatosPaginaComunicado"
            ws_headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Referer": page_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            resp = self.client.post(ws_url, json={}, headers=ws_headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("d", {})
                if isinstance(data, dict):
                    asunto = data.get("Asunto_1") or f"Comunicado {notif_id}"
                    cuerpo_html = data.get("Mensaje_1") or ""
                    soup_body = BeautifulSoup(cuerpo_html, "html.parser")
                    cuerpo_text = soup_body.get_text("\n", strip=True)

                    f_pub = data.get("FechaPublicacion") or ""
                    h_pub = data.get("HoraPublicacion") or ""
                    fecha_completa = f"{f_pub} {h_pub}".strip() or None
                    emisor = data.get("NombreEmisor")

                    attachments: List[AttachmentItem] = []
                    for att in data.get("AdjuntosExistentes", []) or []:
                        att_id = str(att.get("Id") or "")
                        att_nombre = str(att.get("Nombre") or "adjunto.pdf")
                        att_tam = att.get("Tamanio")
                        att_url = (
                            f"{self.client.base_url}/ACWeb/Controladores/ControladorRepositorio.ashx?"
                            f"tipo=6&nombre={att_id}"
                        )
                        attachments.append(
                            AttachmentItem(
                                id=att_id,
                                filename=att_nombre,
                                url=att_url,
                                size=att_tam,
                            )
                        )

                    detail = NotificationDetail(
                        id=notif_id,
                        title=asunto,
                        body=cuerpo_text,
                        date=fecha_completa,
                        sender=emisor,
                        read=True,
                        attachments=attachments,
                        raw=data,
                    )
        except Exception:
            pass

        # 2. Secondary fallback: WSComunicaciones.asmx/GetComunicado
        if not detail:
            try:
                resp = self.client.post(
                    f"{self.client.base_url}/ACWeb/WS_Data/WSComunicaciones.asmx/GetComunicado",
                    json={"id": notif_id},
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=6,
                )
                if resp.status_code == 200:
                    data = resp.json().get("d", {})
                    if data and isinstance(data, dict):
                        attachments = []
                        for att in data.get("Adjuntos") or data.get("Archivos") or []:
                            attachments.append(
                                AttachmentItem(
                                    id=str(att.get("Id", "")),
                                    filename=att.get("Nombre") or "adjunto.pdf",
                                    url=att.get("Url"),
                                    token=att.get("Token"),
                                    size=att.get("Tamano"),
                                )
                            )
                        detail = NotificationDetail(
                            id=notif_id,
                            title=data.get("Titulo") or data.get("Asunto") or f"Comunicado {notif_id}",
                            body=data.get("Cuerpo") or data.get("Contenido") or data.get("Texto") or "",
                            date=data.get("Fecha"),
                            sender=data.get("Remitente"),
                            read=bool(data.get("Leido", True)),
                            attachments=attachments,
                            raw=data,
                        )
            except Exception:
                pass

        if not detail:
            detail = NotificationDetail(
                id=notif_id,
                title=f"Comunicado {notif_id}",
                body="No se pudo obtener el cuerpo detallado del comunicado.",
            )

        # Download attachments if requested
        if download_attachments and detail.attachments:
            out_dir = Path(download_dir or ".").expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            for att in detail.attachments:
                try:
                    dest_file = out_dir / att.filename
                    if att.url and "ControladorRepositorio.ashx" in att.url:
                        # Direct authenticated download
                        r_down = self.client.get(att.url, stream=True, timeout=15)
                        if r_down.status_code == 200:
                            with open(dest_file, "wb") as f:
                                for chunk in r_down.iter_content(chunk_size=65536):
                                    if chunk:
                                        f.write(chunk)
                    elif att.token or (att.url and "token=" in att.url):
                        # Public repository download
                        repo = RepositoryDownloader(session=self.client.session)
                        res = repo.download(
                            token=att.token,
                            url=att.url,
                            output_path=str(out_dir),
                        )
                        att.filename = res.filename
                except Exception:
                    pass

        return detail

    def mark_as_read(self, notif_id: str) -> bool:
        """
        Marks an announcement/notification as read in Alexia using WSHome.asmx/MarcarComunicadoLeidoBadge.
        """
        self._ensure_authenticated()
        url = f"{self.client.base_url}/ACWeb/WS_Data/WSHome.asmx/MarcarComunicadoLeidoBadge"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Referer": f"{self.client.base_url}/ACWeb/paginas/Home/HomeMetro.aspx",
            "X-Requested-With": "XMLHttpRequest",
        }
        resp = self.client.post(url, json={"guidComunicado": notif_id}, headers=headers, timeout=8)
        return resp.status_code == 200

