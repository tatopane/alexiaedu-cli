from typer.testing import CliRunner
from alexia.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CLI para Alexia Familias" in result.stdout


def test_cli_download_missing_args():
    result = runner.invoke(app, ["download"])
    assert result.exit_code == 1
    assert "Debes especificar al menos --token o --url" in result.stderr or "Debes especificar" in result.stdout


def test_cli_auth_status_no_session(monkeypatch, tmp_path):
    monkeypatch.setenv("ALEXIA_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["auth", "status", "--no-remote"])
    assert result.exit_code == 0
    assert "No hay ninguna sesión guardada" in result.stdout


def test_cli_auth_logout(monkeypatch, tmp_path):
    monkeypatch.setenv("ALEXIA_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    assert "No había ninguna sesión activa guardada" in result.stdout
