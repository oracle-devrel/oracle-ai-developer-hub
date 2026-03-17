"""CLI commands for live document sync."""

import typer
from rich.console import Console
from rich.table import Table

from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="Live document sync management")
console = Console()


@app.command()
def add(
    path: str = typer.Argument(..., help="Path or URL to sync"),
    source_type: str = typer.Option("directory", "--type", help="directory, git, or url"),
    pattern: str = typer.Option(None, "--pattern", help="Glob pattern (e.g. '*.md,*.txt')"),
    interval: int = typer.Option(300, "--interval", help="Poll interval in seconds"),
):
    """Add a sync source."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.sync.scheduler import SyncScheduler
        scheduler = SyncScheduler(conn, config.get('sync', {}))

        source_id = scheduler.add_source(
            source_type=source_type,
            path=path,
            glob_pattern=pattern,
            poll_interval=interval,
        )
        console.print(f"[green]Sync source added:[/] {source_id}")
        console.print(f"  Type: {source_type}")
        console.print(f"  Path: {path}")
        if pattern:
            console.print(f"  Pattern: {pattern}")
        console.print(f"  Interval: {interval}s")
    except Exception as e:
        console.print(f"[red]Failed to add sync source: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command(name="list")
def list_sources():
    """List all sync sources."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.sync.scheduler import SyncScheduler
        scheduler = SyncScheduler(conn, config.get('sync', {}))

        sources = scheduler.list_sources()
        if not sources:
            console.print("[yellow]No sync sources configured.[/]")
            raise typer.Exit(0)

        table = Table(title="Sync Sources")
        table.add_column("ID", style="cyan", max_width=12)
        table.add_column("Type")
        table.add_column("Path", max_width=40)
        table.add_column("Pattern")
        table.add_column("Interval")
        table.add_column("Enabled")
        table.add_column("Last Sync")

        for s in sources:
            table.add_row(
                s['source_id'][:12],
                s.get('source_type', ''),
                s.get('source_path', ''),
                s.get('glob_pattern', '-'),
                f"{s.get('poll_interval', 300)}s",
                "Yes" if s.get('enabled', 1) else "No",
                str(s.get('last_sync', '-'))[:19] if s.get('last_sync') else '-',
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to list sources: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def status():
    """Show sync status overview."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.sync.scheduler import SyncScheduler
        scheduler = SyncScheduler(conn, config.get('sync', {}))

        sync_status = scheduler.get_sync_status()
        console.print("[bold]Sync Status[/]")
        console.print(f"  Total sources: {sync_status.get('total_sources', 0)}")
        console.print(f"  Enabled sources: {sync_status.get('enabled_sources', 0)}")
        console.print(f"  Recent events: {sync_status.get('recent_event_count', 0)}")
    except Exception as e:
        console.print(f"[red]Failed to get sync status: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def remove(
    source_id: str = typer.Argument(..., help="Source ID to remove"),
):
    """Remove a sync source."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.sync.scheduler import SyncScheduler
        scheduler = SyncScheduler(conn, config.get('sync', {}))
        scheduler.remove_source(source_id)
        console.print(f"[green]Removed sync source:[/] {source_id}")
    except Exception as e:
        console.print(f"[red]Failed to remove source: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def events(
    limit: int = typer.Option(20, "--limit", help="Max events to show"),
):
    """Show recent sync events."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.sync.scheduler import SyncScheduler
        scheduler = SyncScheduler(conn, config.get('sync', {}))

        event_list = scheduler.get_recent_events(limit=limit)
        if not event_list:
            console.print("[yellow]No sync events found.[/]")
            raise typer.Exit(0)

        table = Table(title="Recent Sync Events")
        table.add_column("Event ID", style="cyan", max_width=12)
        table.add_column("Type")
        table.add_column("File", max_width=30)
        table.add_column("Added", justify="right")
        table.add_column("Removed", justify="right")
        table.add_column("Unchanged", justify="right")
        table.add_column("Time")

        for e in event_list:
            table.add_row(
                e['event_id'][:12],
                e.get('event_type', ''),
                e.get('file_path', '')[-30:],
                str(e.get('chunks_added', 0)),
                str(e.get('chunks_removed', 0)),
                str(e.get('chunks_unchanged', 0)),
                str(e.get('processed_at', ''))[:19],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to list events: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()
