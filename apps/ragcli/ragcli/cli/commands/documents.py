"""Document management commands for ragcli CLI."""

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from typing import Optional

app = typer.Typer()
console = Console()

def list_documents(config, format='table', verbose=False):
    """Helper to list documents."""
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT document_id, filename, file_format, upload_timestamp, chunk_count, total_tokens
            FROM DOCUMENTS
            ORDER BY upload_timestamp DESC
        """)
        rows = cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()
    
    if format == 'table':
        table = Table(
            title="   Managed Intelligence Assets", 
            show_header=True,
            box=None,
            header_style="bold #a855f7",
            title_style="bold white",
            padding=(0, 2)
        )
        table.add_column("ID", style="dim white")
        table.add_column("Filename", style="#9333ea")
        table.add_column("Format", style="#a855f7")
        table.add_column("Uploaded", style="dim white")
        table.add_column("Chunks", justify="right", style="#9333ea")
        table.add_column("Tokens", justify="right", style="#a855f7")
        
        for row in rows:
            # Shorten ID for display
            display_id = row[0][:8] + "..." if len(row[0]) > 10 else row[0]
            table.add_row(display_id, row[1], row[2], str(row[3]), str(row[4]), str(row[5]))
        console.print(table)
    else:
        # JSON or other
        import json
        docs = [{'id': r[0], 'filename': r[1], 'format': r[2], 'uploaded': str(r[3]), 'chunks': r[4], 'tokens': r[5]} for r in rows]
        rprint(json.dumps(docs, indent=2))

@app.command()
def list_docs(
    format: str = typer.Option("table", "--format", help="Output format (table, json)"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """List all uploaded documents."""
    config = load_config()
    list_documents(config, format, verbose)

@app.command()
def delete(doc_id: str):
    """Delete a document by ID."""
    config = load_config()
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DOCUMENTS WHERE document_id = :doc_id", {'doc_id': doc_id})
        conn.commit()
        if cursor.rowcount > 0:
            rprint(typer.style(f"Deleted document {doc_id}", fg=typer.colors.GREEN))
        else:
            rprint(typer.style(f"Document {doc_id} not found.", fg=typer.colors.YELLOW))
    except Exception as e:
        rprint(typer.style(f"Delete failed: {e}", fg=typer.colors.RED))
        if conn: conn.rollback()
        raise typer.Exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()

if __name__ == "__main__":
    app()
