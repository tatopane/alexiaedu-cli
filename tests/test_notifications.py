import responses
from alexia.client import AlexiaClient
from alexia.models import AuthSession
from alexia.notifications import NotificationService


@responses.activate
def test_list_notifications_get_wp_detalle():
    session_obj = AuthSession(
        user="test_user",
        token="token_uuid",
        rol="1001",
        cookies={".ASPXAUTH": "dummyauth"},
    )
    client = AlexiaClient(session_obj=session_obj, auto_load=False)

    dto_url = "https://web2.alexiaedu.com/ACWeb/WS_Data/WSHome.asmx/GetWPDetalleDTO"
    responses.add(
        responses.POST,
        dto_url,
        json={
            "d": {
                "Items": [
                    {
                        "Id": "guid-com-1",
                        "Title": "Circular Informativa Trimestral",
                        "Subtitle": "de: Colegio de Prueba",
                        "RightSubtitle": "26/11/2026",
                        "Data": {
                            "Guid": "guid-com-1",
                            "Titulo": "Circular Informativa Trimestral",
                            "IsLeido": False,
                        },
                        "OnClick": {
                            "Url": "~/paginas/Comunicacion/Comunicado.aspx?GuidComunicadoOrigen=guid-com-1"
                        },
                    }
                ]
            }
        },
        status=200,
    )

    service = NotificationService(client=client)
    items = service.list_notifications()

    assert len(items) == 1
    assert items[0].id == "guid-com-1"
    assert items[0].title == "Circular Informativa Trimestral"
    assert items[0].sender == "Colegio de Prueba"
    assert items[0].date == "26/11/2026"
    assert items[0].read is False


@responses.activate
def test_get_notification_detail_ws_comunicados():
    session_obj = AuthSession(
        user="test_user",
        token="token_uuid",
        rol="1001",
        cookies={".ASPXAUTH": "dummyauth"},
    )
    client = AlexiaClient(session_obj=session_obj, auto_load=False)

    guid = "guid-1234"
    page_url = f"https://web2.alexiaedu.com/ACWeb/paginas/Comunicacion/Comunicado.aspx?GuidComunicadoOrigen={guid}&TipoComunicado=N&AccionComunicado=1&master=2"
    responses.add(responses.GET, page_url, body="<html>OK</html>", status=200)

    ws_url = "https://web2.alexiaedu.com/ACWeb/WS_Data/WSComunicados.asmx/GetDatosPaginaComunicado"
    responses.add(
        responses.POST,
        ws_url,
        json={
            "d": {
                "Asunto_1": "Circular Importante",
                "Mensaje_1": "<p>Estimadas familias, adjuntamos archivo.</p>",
                "FechaPublicacion": "2026-11-26",
                "HoraPublicacion": "16:00",
                "NombreEmisor": "Colegio de Prueba",
                "AdjuntosExistentes": [
                    {
                        "Id": "archivo1.pdf",
                        "Nombre": "CircularNavidad.pdf",
                        "Tamanio": 10240,
                    }
                ],
            }
        },
        status=200,
    )

    service = NotificationService(client=client)
    detail = service.get_notification(notif_id=guid)

    assert detail.id == guid
    assert detail.title == "Circular Importante"
    assert "Estimadas familias" in detail.body
    assert detail.sender == "Colegio de Prueba"
    assert len(detail.attachments) == 1
    assert detail.attachments[0].filename == "CircularNavidad.pdf"
    assert "tipo=6&nombre=archivo1.pdf" in detail.attachments[0].url


@responses.activate
def test_mark_as_read_success():
    session_obj = AuthSession(
        user="test_user",
        token="token_uuid",
        rol="1001",
        cookies={".ASPXAUTH": "dummyauth"},
    )
    client = AlexiaClient(session_obj=session_obj, auto_load=False)

    guid = "00000000-0000-0000-0000-000000000001"
    badge_url = "https://web2.alexiaedu.com/ACWeb/WS_Data/WSHome.asmx/MarcarComunicadoLeidoBadge"
    responses.add(
        responses.POST,
        badge_url,
        json={"d": {"Codigo": "comunicados", "Contador": 5}},
        status=200,
    )

    service = NotificationService(client=client)
    ok = service.mark_as_read(guid)
    assert ok is True
