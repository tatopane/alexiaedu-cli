import responses
from typer.testing import CliRunner

from alexia.cli import app
from alexia.client import AlexiaClient
from alexia.models import AuthSession
from alexia.students import StudentService

runner = CliRunner()


HTML_HOME_SAMPLE = """
<html>
<body>
<ul id="ctl00_ContenidoPagina_ctl07_cmptHijosSeg_lienzo_hijos">
  <li hijo="guid-hijo-1">
    <img src="/ACWeb/controladores/ControladorFotografias.ashx?tipo=2&key=persona-key-1" />
    <p>Lucas García</p>
  </li>
  <li hijo="guid-hijo-2">
    <img src="/ACWeb/controladores/ControladorFotografias.ashx?tipo=2&key=persona-key-2" />
    <p>Sofía García</p>
  </li>
</ul>
<ul id="ctl00_ContenidoPagina_contenido_agenda_cmptHijo_lista_users">
  <li class="hijo" onclick="javascript:HijoClicked(this, 'persona-key-1', 'False');">
    <strong>Hijo</strong>
    <h3>Lucas</h3>
  </li>
  <li class="hijo" onclick="javascript:HijoClicked(this, 'persona-key-2', 'False');">
    <strong>Hija</strong>
    <h3>Sofía</h3>
  </li>
</ul>
</body>
</html>
"""

CALIF_SAMPLE_1 = """
<div>
  <select id="ctl00_cmbMatricula">
    <option value="1">Castor verde</option>
    <option value="2">Comedor Mensual</option>
  </select>
</div>
"""

CALIF_SAMPLE_2 = """
<div>
  <select id="ctl00_cmbMatricula">
    <option value="10">Tercero de Primaria B</option>
    <option value="20">Fútbol</option>
  </select>
</div>
"""


@responses.activate
def test_list_students_service():
    session_obj = AuthSession(
        user="test_user",
        token="token_uuid",
        rol="1001",
        cookies={".ASPXAUTH": "dummyauth"},
    )
    client = AlexiaClient(session_obj=session_obj, auto_load=False)

    home_url = "https://web2.alexiaedu.com/ACWeb/paginas/Home/HomeMetro.aspx"
    responses.add(responses.GET, home_url, body=HTML_HOME_SAMPLE, status=200)

    calif_url = "https://web2.alexiaedu.com/ACWeb/WS_Data/WSHome.asmx/GetWPCalificaciones"
    responses.add(
        responses.POST,
        calif_url,
        json={"d": {"calificaciones": CALIF_SAMPLE_1}},
        status=200,
    )
    responses.add(
        responses.POST,
        calif_url,
        json={"d": {"calificaciones": CALIF_SAMPLE_2}},
        status=200,
    )

    service = StudentService(client=client)
    students = service.list_students(fetch_academic=True)

    assert len(students) == 2
    assert students[0].nombre == "Lucas García"
    assert students[0].parentesco == "Hijo"
    assert students[0].curso == "Castor verde"
    assert "Comedor Mensual" in students[0].matriculas

    assert students[1].nombre == "Sofía García"
    assert students[1].parentesco == "Hija"
    assert students[1].curso == "Tercero de Primaria B"
    assert "Fútbol" in students[1].matriculas


def test_cli_students_help():
    result = runner.invoke(app, ["students", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout

    result_alumnos = runner.invoke(app, ["alumnos", "--help"])
    assert result_alumnos.exit_code == 0
    assert "list" in result_alumnos.stdout
