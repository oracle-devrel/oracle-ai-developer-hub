"""Database commands for ragcli CLI."""

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient

app = typer.Typer()
console = Console()

@app.command()
def init():
    """Initialize the database schemas and vector index."""
    try:
        config = load_config()
        client = OracleClient(config)
        client.init_db()
        client.close()
        console.print("[green]✓ Database initialized successfully![/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize database: {e}[/red]")
        raise


@app.command()
def browse(
    table: str = typer.Option("DOCUMENTS", "--table", "-t", help="Table to browse (DOCUMENTS, CHUNKS, QUERIES)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of rows to display"),
    offset: int = typer.Option(0, "--offset", "-o", help="Row offset for pagination")
):
    """Browse database tables with pagination."""
    config = load_config()
    
    table = table.upper()
    valid_tables = ["DOCUMENTS", "CHUNKS", "QUERIES"]
    
    if table not in valid_tables:
        console.print(f"[red]Invalid table. Choose from: {', '.join(valid_tables)}[/red]")
        raise typer.Exit(1)
    
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total_count = cursor.fetchone()[0]
        
        if total_count == 0:
            console.print(f"[yellow]Table {table} is empty[/yellow]")
            return
        
        # Define columns for each table
        if table == "DOCUMENTS":
            query = f"""
                SELECT document_id, filename, file_format, file_size_bytes, 
                       chunk_count, total_tokens, upload_timestamp
                FROM {table}
                ORDER BY upload_timestamp DESC
                OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
            """
            columns = ["ID", "Filename", "Format", "Size (KB)", "Chunks", "Tokens", "Uploaded"]
        elif table == "CHUNKS":
            query = f"""
                SELECT chunk_id, document_id, chunk_number, token_count, 
                       SUBSTR(chunk_text, 1, 50) as preview
                FROM {table}
                ORDER BY document_id, chunk_number
                OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
            """
            columns = ["Chunk ID", "Document ID", "Index", "Tokens", "Preview"]
        else:  # QUERIES
            query = f"""
                SELECT query_id, query_text, SUBSTR(response_text, 1, 50) as response_preview, 
                       created_at
                FROM {table}
                ORDER BY created_at DESC
                OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY
            """
            columns = ["Query ID", "Query", "Response Preview", "Created"]
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Create table
        rich_table = Table(title=f"{table} (Rows {offset+1}-{min(offset+limit, total_count)} of {total_count})")
        
        for col in columns:
            rich_table.add_column(col, style="cyan")
        
        for row in rows:
            formatted_row = []
            for i, val in enumerate(row):
                if columns[i] == "Size (KB)":
                    formatted_row.append(f"{val/1024:.2f}")
                elif isinstance(val, (int, float)):
                    formatted_row.append(str(val))
                else:
                    formatted_row.append(str(val) if val else "N/A")
            rich_table.add_row(*formatted_row)
        
        console.print(rich_table)
        
        # Show pagination info
        has_more = (offset + limit) < total_count
        has_prev = offset > 0
        
        pagination_info = []
        if has_prev:
            pagination_info.append(f"Previous: --offset {max(0, offset-limit)}")
        if has_more:
            pagination_info.append(f"Next: --offset {offset+limit}")
        
        if pagination_info:
            console.print("\n[dim]" + " | ".join(pagination_info) + "[/dim]")

    except Exception as e:
        console.print(f"[red]Error browsing table: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()


@app.command()
def query(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, csv)")
):
    """Execute a custom SQL query and display results."""
    config = load_config()
    
    # Safety check - only allow SELECT queries
    if not sql.strip().upper().startswith("SELECT"):
        console.print("[red]Only SELECT queries are allowed for safety[/red]")
        raise typer.Exit(1)
    
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if not rows:
            console.print("[yellow]Query returned no results[/yellow]")
            return
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        if format == "table":
            # Rich table output
            rich_table = Table(title=f"Query Results ({len(rows)} rows)")
            
            for col in columns:
                rich_table.add_column(col, style="cyan")
            
            for row in rows:
                rich_table.add_row(*[str(val) if val is not None else "NULL" for val in row])
            
            console.print(rich_table)
            
        elif format == "json":
            # JSON output
            import json
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            console.print(json.dumps(result, indent=2, default=str))
            
        elif format == "csv":
            # CSV output
            import csv
            import sys
            writer = csv.writer(sys.stdout)
            writer.writerow(columns)
            writer.writerows(rows)

    except Exception as e:
        console.print(f"[red]Query execution failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()


@app.command()
def stats():
    """Show database statistics and table sizes."""
    config = load_config()
    
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        stats_table = Table(title="Database Statistics")
        stats_table.add_column("Table", style="cyan")
        stats_table.add_column("Row Count", style="yellow")
        stats_table.add_column("Size Info", style="green")
        
        tables = ["DOCUMENTS", "CHUNKS", "QUERIES"]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                if table == "DOCUMENTS":
                    cursor.execute("SELECT SUM(file_size_bytes) FROM DOCUMENTS")
                    total_size = cursor.fetchone()[0] or 0
                    size_info = f"Total: {total_size/1024/1024:.2f} MB"
                elif table == "CHUNKS":
                    cursor.execute("SELECT SUM(token_count) FROM CHUNKS")
                    total_tokens = cursor.fetchone()[0] or 0
                    size_info = f"Total tokens: {total_tokens:,}"
                else:
                    size_info = "-"
                
                stats_table.add_row(table, f"{count:,}", size_info)
            except:
                stats_table.add_row(table, "N/A", "Table may not exist")
        
        console.print(stats_table)
    except Exception as e:
        console.print(f"[red]Error getting stats: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()


if __name__ == "__main__":
    app()
