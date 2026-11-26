from datetime import datetime
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from alexia import config, storage
from alexia.auth import AlexiaAuth
from alexia.client import AlexiaClient
from alexia.notifications import NotificationService
from alexia.repository import RepositoryDownloader
from alexia.students import StudentService

app = typer.Typer(
    name="alexia",
    help="CLI para Alexia Familias (Everest School).",
    no_args_is_help=True,
)
auth_app = typer.Typer(name="auth", help="Gestión de autenticación y sesiones.")
notif_app = typer.Typer(name="notif", help="Gestión de notificaciones y comunicados.")
students_app = typer.Typer(name="students", help="Consulta de alumnos e hijos matriculados.")

app.add_typer(auth_app, name="auth")
app.add_typer(notif_app, name="notif")
app.add_typer(students_app, name="students")
app.add_typer(students_app, name="alumnos")

console = Console()
err_console = Console(stderr=True)


# ==============================================================================
# AUTH COMMANDS
# ==============================================================================


@auth_app.command("login")
def auth_login(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="Usuario de Alexia"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Contraseña de Alexia (se solicita de forma segura si no se indica)",
    ),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="ID de rol específico"),
):
    """Inicia sesión en Alexia Familias y guarda la sesión localmente."""
    from_env_user = False
    from_env_pass = False

    if not user:
        env_u = config.get_default_user()
        if env_u:
            user = env_u
            from_env_user = True
        else:
            user = typer.prompt("Usuario de Alexia")

    if not password:
        env_p = config.get_default_password()
        if env_p:
            password = env_p
            from_env_pass = True
        else:
            password = typer.prompt("Contraseña", hide_input=True)

    if from_env_user and from_env_pass:
        console.print("[dim]ℹ Utilizando credenciales configuradas en el entorno (.env)[/dim]")

    with console.status("[bold blue]Autenticando en Everest School (Alexia)..."):
        try:
            auth_service = AlexiaAuth()
            session_obj = auth_service.login(usuario=user, contrasena=password, role_id=role)
            saved_file = storage.save_session(session_obj)
        except Exception as e:
            err_console.print(f"[bold red]Error en el login:[/bold red] {e}")
            raise typer.Exit(code=1)

    console.print(f"[bold green]✔ Sesión iniciada correctamente[/bold green]")
    console.print(f"Usuario: [bold cyan]{session_obj.user}[/bold cyan]")
    console.print(f"Rol asignado: [bold yellow]{session_obj.rol}[/bold yellow]")
    if session_obj.ruta_home:
        console.print(f"Ruta Home: {session_obj.ruta_home}")
    console.print(f"Guardado en: [dim]{saved_file}[/dim]")


@auth_app.command("status")
def auth_status(
    check_remote: bool = typer.Option(True, "--remote/--no-remote", help="Verificar sesión con el servidor remoto"),
):
    """Muestra el estado de la sesión actual."""
    client = AlexiaClient(auto_load=True)
    if not client.session_obj:
        console.print("[yellow]No hay ninguna sesión guardada.[/yellow]")
        console.print("Usa [bold]alexia auth login[/bold] para iniciar sesión.")
        raise typer.Exit(code=0)

    session = client.session_obj
    table = Table(title="Estado de Sesión Alexia", show_header=True)
    table.add_column("Propiedad", style="cyan")
    table.add_column("Valor", style="white")

    table.add_row("Usuario", session.user or "Desconocido")
    table.add_row("Rol", session.rol or "N/A")
    table.add_row("Token UUID", session.token[:8] + "..." if session.token else "N/A")
    table.add_row("Fecha guardada", session.created_at)
    table.add_row("Cookie .ASPXAUTH", "[green]Presente[/green]" if session.is_authenticated else "[red]Ausente[/red]")

    if check_remote:
        status_info = client.check_status()
        if status_info.get("authenticated"):
            table.add_row("Servidor", "[bold green]Conexión y sesión activas[/bold green]")
        else:
            table.add_row("Servidor", f"[bold red]Sesión inactiva:[/bold red] {status_info.get('reason')}")

    console.print(table)


@auth_app.command("logout")
def auth_logout():
    """Cierra la sesión local y borra las credenciales guardadas."""
    cleared = storage.clear_session()
    if cleared:
        console.print("[green]✔ Sesión eliminada correctamente.[/green]")
    else:
        console.print("[yellow]No había ninguna sesión activa guardada.[/yellow]")


# ==============================================================================
# DOWNLOAD COMMAND
# ==============================================================================


@app.command("download")
def download_cmd(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Token del documento (desde link de correo)"),
    url: Optional[str] = typer.Option(None, "--url", help="URL completa de Repositorio.aspx"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Ruta o nombre de archivo de salida"),
):
    """Descarga circulares o archivos públicos de Repositorio.aspx sin login."""
    if not token and not url:
        err_console.print("[bold red]Error:[/bold red] Debes especificar al menos --token o --url.")
        raise typer.Exit(code=1)

    downloader = RepositoryDownloader()
    with console.status("[bold blue]Descargando circular desde Alexia..."):
        try:
            result = downloader.download(token=token, url=url, output_path=output)
        except Exception as e:
            err_console.print(f"[bold red]Error al descargar archivo:[/bold red] {e}")
            raise typer.Exit(code=1)

    size_kb = round(result.size_bytes / 1024, 1)
    console.print(f"[bold green]✔ Descarga completada[/bold green]")
    console.print(f"Archivo: [bold cyan]{result.filename}[/bold cyan] ({size_kb} KB)")
    console.print(f"Ruta: [dim]{result.saved_path}[/dim]")


# ==============================================================================
# NOTIFICATIONS COMMANDS
# ==============================================================================


@notif_app.command("list")
def notif_list(
    unread: bool = typer.Option(False, "--unread", "-u", help="Mostrar solo comunicados no leídos"),
    limit: int = typer.Option(10, "--limit", "-l", help="Número máximo de comunicados a listar"),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
):
    """Lista las notificaciones y circulares del usuario."""
    service = NotificationService()
    with console.status("[bold blue]Consultando comunicados..."):
        try:
            items = service.list_notifications(unread_only=unread, limit=limit)
        except Exception as e:
            err_console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    if json_output:
        print(json.dumps([item.model_dump() for item in items], indent=2, ensure_ascii=False))
        return

    if not items:
        console.print("[yellow]No se encontraron comunicados disponibles.[/yellow]")
        return

    table = Table(title="Comunicados y Circulares", show_header=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Fecha", style="cyan", width=12)
    table.add_column("Remitente", style="yellow", width=18)
    table.add_column("Título", style="white")
    table.add_column("Estado", style="green", width=10)

    for it in items:
        status_str = "[dim]Leído[/dim]" if it.read else "[bold green]No leído[/bold green]"
        table.add_row(
            it.id,
            it.date or "-",
            it.sender or "-",
            it.title + (" [dim]📎[/dim]" if it.has_attachments else ""),
            status_str,
        )

    console.print(table)


@notif_app.command("get")
def notif_get(
    notif_id: str = typer.Argument(..., help="ID del comunicado a consultar"),
    download_attachments: bool = typer.Option(
        False,
        "--download-attachments",
        "-d",
        help="Descargar automáticamente los archivos adjuntos",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "-o",
        "--output-dir",
        help="Directorio de destino para los adjuntos",
    ),
):
    """Muestra el detalle de un comunicado y opcionalmente descarga adjuntos."""
    service = NotificationService()
    with console.status(f"[bold blue]Obteniendo comunicado {notif_id}..."):
        try:
            detail = service.get_notification(
                notif_id=notif_id,
                download_attachments=download_attachments,
                download_dir=output_dir,
            )
        except Exception as e:
            err_console.print(f"[bold red]Error al obtener comunicado:[/bold red] {e}")
            raise typer.Exit(code=1)

    panel_text = f"[bold cyan]{detail.title}[/bold cyan]\n"
    if detail.date:
        panel_text += f"[dim]Fecha:[/dim] {detail.date}\n"
    if detail.sender:
        panel_text += f"[dim]De:[/dim] {detail.sender}\n"
    panel_text += "\n" + (detail.body or "[italic]Sin contenido de texto[/italic]")

    if detail.attachments:
        panel_text += "\n\n[bold yellow]Adjuntos:[/bold yellow]\n"
        for att in detail.attachments:
            panel_text += f" • {att.filename}\n"

    console.print(Panel(panel_text, title=f"Comunicado #{detail.id}", expand=False))


@notif_app.command("mark-read")
def notif_mark_read(
    notif_id: str = typer.Argument(..., help="ID del comunicado a marcar como leído"),
):
    """Marca un comunicado específico como leído."""
    service = NotificationService()
    with console.status(f"[bold blue]Marcando comunicado {notif_id} como leído..."):
        try:
            ok = service.mark_as_read(notif_id)
        except Exception as e:
            err_console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    if ok:
        console.print(f"[bold green]✔ Comunicado {notif_id} marcado como leído.[/bold green]")
    else:
        err_console.print(f"[bold red]Error al marcar como leído el comunicado {notif_id}[/bold red]")
        raise typer.Exit(code=1)


@notif_app.command("mark-all-read")
def notif_mark_all_read(
    older_than_hours: int = typer.Option(
        24,
        "--older-than-hours",
        "-h",
        help="Antigüedad mínima en horas para marcar como leído (por defecto 24 horas)",
    ),
    limit: int = typer.Option(100, "--limit", "-l", help="Máximo de comunicados a evaluar"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo listar los que se marcarían sin modificarlos"),
):
    """Marca como leídos los comunicados no leídos con una antigüedad superior a las horas indicadas."""
    service = NotificationService()
    with console.status("[bold blue]Consultando comunicados no leídos..."):
        try:
            items = service.list_notifications(unread_only=True, limit=limit)
        except Exception as e:
            err_console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    now = datetime.now()
    to_mark = []
    skipped = []

    for it in items:
        is_older = False
        if it.date:
            try:
                # Format: DD/MM/YYYY
                dt = datetime.strptime(it.date, "%d/%m/%Y")
                # Add 23h59m if notice was published on that date, or compare days
                diff_hours = (now - dt).total_seconds() / 3600.0
                if diff_hours >= older_than_hours:
                    is_older = True
            except Exception:
                pass

        if is_older:
            to_mark.append(it)
        else:
            skipped.append(it)

    if not to_mark:
        console.print(f"[yellow]No hay comunicados no leídos con más de {older_than_hours}h de antigüedad.[/yellow]")
        if skipped:
            console.print(f"[dim]Se omitieron {len(skipped)} comunicados recientes (menos de {older_than_hours}h).[/dim]")
        return

    console.print(f"Se encontraron [bold cyan]{len(to_mark)}[/bold cyan] comunicados con más de {older_than_hours}h de antigüedad.")

    if dry_run:
        console.print("[yellow]Modo --dry-run activo. No se realizarán cambios en el servidor.[/yellow]")
        for it in to_mark:
            console.print(f" - [dim]{it.date}[/dim] {it.title} ([dim]{it.id}[/dim])")
        return

    marked_count = 0
    with console.status("[bold blue]Marcando comunicados en el servidor..."):
        for it in to_mark:
            try:
                if service.mark_as_read(it.id):
                    marked_count += 1
            except Exception as e:
                err_console.print(f"[red]Error marcando {it.id}:[/red] {e}")

    console.print(f"[bold green]✔ Se han marcado como leídos {marked_count} de {len(to_mark)} comunicados.[/bold green]")
    if skipped:
        console.print(f"[dim]Permanecen sin leer {len(skipped)} comunicados recientes (< {older_than_hours}h).[/dim]")


# ==============================================================================
# STUDENTS COMMANDS
# ==============================================================================


@students_app.command("list")
def students_list(
    details: bool = typer.Option(
        True,
        "--details/--no-details",
        help="Consultar curso y asignaturas/matrículas activas",
    ),
    json_output: bool = typer.Option(False, "--json", help="Salida en formato JSON"),
):
    """Lista los alumnos e hijos vinculados a la cuenta familiar."""
    service = StudentService()
    with console.status("[bold blue]Consultando alumnos vinculados..."):
        try:
            students = service.list_students(fetch_academic=details)
        except Exception as e:
            err_console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    if json_output:
        print(json.dumps([s.model_dump() for s in students], indent=2, ensure_ascii=False))
        return

    if not students:
        console.print("[yellow]No se encontraron alumnos registrados en esta cuenta.[/yellow]")
        return

    table = Table(title="Alumnos e Hijos Registrados", show_header=True)
    table.add_column("Nombre", style="bold cyan")
    table.add_column("Parentesco", style="yellow", width=12)
    table.add_column("Curso / Clase", style="white")
    table.add_column("Otras Matrículas / Actividades", style="dim")
    table.add_column("ID Alumno", style="dim", width=12)

    for st in students:
        otras = [m for m in st.matriculas if m != st.curso]
        otras_str = ", ".join(otras) if otras else "-"
        table.add_row(
            st.nombre,
            st.parentesco,
            st.curso or "-",
            otras_str,
            st.id[:8] + "..." if st.id else "-",
        )

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
