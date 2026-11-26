import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
from bs4 import BeautifulSoup
import requests

from alexia.auth import DEFAULT_USER_AGENT
from alexia.models import DownloadResult

REPOSITORIO_URL_BASE = "https://web2.alexiaedu.com/ACWeb/paginas/publicas/Repositorio.aspx"


def extract_token_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    tokens = qs.get("token")
    if tokens:
        return tokens[0]
    return None


def parse_content_disposition(cd_header: Optional[str]) -> Optional[str]:
    if not cd_header:
        return None

    # Try filename*=UTF-8''...
    match_utf8 = re.search(r"filename\*=UTF-8''([^;]+)", cd_header, re.IGNORECASE)
    if match_utf8:
        return unquote(match_utf8.group(1).strip('"\''))

    # Try filename="..." or filename=...
    match = re.search(r'filename="?([^";]+)"?', cd_header, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


class RepositoryDownloader:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        base_url: str = REPOSITORIO_URL_BASE,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.session = session or requests.Session()
        self.base_url = base_url
        self.user_agent = user_agent
        self.session.headers.update({
            "User-Agent": self.user_agent,
        })

    def download(
        self,
        token: Optional[str] = None,
        url: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> DownloadResult:
        if not token and not url:
            raise ValueError("Se debe proporcionar un token o una URL de repositorio.")

        target_url = url
        if not target_url:
            target_url = f"{self.base_url}?token={token}"
        elif not token:
            extracted = extract_token_from_url(target_url)
            if extracted:
                token = extracted

        # Step 1: GET to retrieve initial form state
        get_resp = self.session.get(target_url)
        get_resp.raise_for_status()

        # Step 2: Extract hidden ASP.NET form inputs
        soup = BeautifulSoup(get_resp.text, "html.parser")
        form = soup.find("form") or soup

        def get_input_val(name: str) -> str:
            inp = form.find("input", {"name": name})
            if inp and inp.get("value"):
                return str(inp.get("value"))
            return ""

        viewstate = get_input_val("__VIEWSTATE")
        viewstategen = get_input_val("__VIEWSTATEGENERATOR")
        eventvalidation = get_input_val("__EVENTVALIDATION")

        if not viewstate:
            # Fallback regex search
            vs_match = re.search(r'id=["\']__VIEWSTATE["\']\s+value=["\']([^"\']*)["\']', get_resp.text)
            if vs_match:
                viewstate = vs_match.group(1)

        # Step 3: POST triggering devolver_fichero postback
        payload = {
            "__EVENTTARGET": "devolver_fichero",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstategen,
            "__EVENTVALIDATION": eventvalidation,
        }

        # Include other hidden inputs that might be present in form
        for inp in form.find_all("input", type="hidden"):
            inp_name = inp.get("name")
            if inp_name and inp_name not in payload and inp.get("value") is not None:
                payload[inp_name] = inp.get("value")

        headers = {
            "Referer": target_url,
            "Origin": "https://web2.alexiaedu.com",
        }

        post_resp = self.session.post(target_url, data=payload, headers=headers, stream=True)
        post_resp.raise_for_status()

        # Step 4: Determine filename and save
        content_disposition = post_resp.headers.get("Content-Disposition")
        extracted_name = parse_content_disposition(content_disposition)
        content_type = post_resp.headers.get("Content-Type")

        default_name = f"circular_{token or 'download'}.pdf"
        chosen_filename = extracted_name or default_name

        if output_path:
            p = Path(output_path).expanduser()
            if p.is_dir() or str(output_path).endswith("/") or str(output_path).endswith("\\"):
                p.mkdir(parents=True, exist_ok=True)
                final_path = p / chosen_filename
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                final_path = p
        else:
            final_path = Path.cwd() / chosen_filename

        total_bytes = 0
        with open(final_path, "wb") as f:
            for chunk in post_resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    total_bytes += len(chunk)

        return DownloadResult(
            filename=final_path.name,
            saved_path=str(final_path.resolve()),
            size_bytes=total_bytes,
            content_type=content_type,
        )
