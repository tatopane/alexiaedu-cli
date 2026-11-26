from pathlib import Path
import responses
from alexia.repository import (
    RepositoryDownloader,
    extract_token_from_url,
    parse_content_disposition,
    REPOSITORIO_URL_BASE,
)


def test_extract_token_from_url():
    url = "https://web2.alexiaedu.com/ACWeb/paginas/publicas/Repositorio.aspx?token=mysecrettoken123"
    assert extract_token_from_url(url) == "mysecrettoken123"

    url_no_token = "https://web2.alexiaedu.com/ACWeb/paginas/publicas/Repositorio.aspx"
    assert extract_token_from_url(url_no_token) is None


def test_parse_content_disposition():
    cd_standard = 'attachment; filename="circular_noviembre.pdf"'
    assert parse_content_disposition(cd_standard) == "circular_noviembre.pdf"

    cd_utf8 = "attachment; filename*=UTF-8''Menu_Escolar%202026.pdf"
    assert parse_content_disposition(cd_utf8) == "Menu_Escolar 2026.pdf"

    assert parse_content_disposition(None) is None


@responses.activate
def test_download_repository_file(tmp_path):
    token = "test-token-777"
    target_url = f"{REPOSITORIO_URL_BASE}?token={token}"

    get_html = """
    <html>
        <form id="form1">
            <input type="hidden" name="__VIEWSTATE" value="viewstate_data_xyz" />
            <input type="hidden" name="__VIEWSTATEGENERATOR" value="gen_123" />
            <input type="hidden" name="__EVENTVALIDATION" value="event_val_456" />
        </form>
    </html>
    """
    responses.add(responses.GET, target_url, body=get_html, status=200)

    pdf_content = b"%PDF-1.4 test circular content"
    responses.add(
        responses.POST,
        target_url,
        body=pdf_content,
        headers={"Content-Disposition": 'attachment; filename="boletin.pdf"'},
        status=200,
    )

    downloader = RepositoryDownloader()
    out_file = tmp_path / "custom_name.pdf"
    result = downloader.download(token=token, output_path=str(out_file))

    assert result.filename == "custom_name.pdf"
    assert Path(result.saved_path).is_file()
    assert Path(result.saved_path).read_bytes() == pdf_content
    assert result.size_bytes == len(pdf_content)
