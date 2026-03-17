"""Oracle AI Vector Search Test Commands."""

import typer
from rich.console import Console
from rich.panel import Panel
from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from ragcli.core.oracle_integration import OracleIntegrationManager
import sys
import os

app = typer.Typer(help="Test Oracle AI Vector Search features")
console = Console()

def get_manager_and_conn():
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        manager = OracleIntegrationManager(conn)
        return manager, client, conn
    except ImportError:
        console.print("[red]langchain-oracledb is not installed.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error initializing Oracle Manager: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def loader(file_path: str):
    """Test OracleDocLoader with a local file."""
    manager, client, conn = get_manager_and_conn()
    try:
        console.print(f"[cyan]Loading {file_path} using OracleDocLoader...[/cyan]")
        docs = manager.load_document(file_path)
        console.print(f"[green]Successfully loaded {len(docs)} document(s).[/green]")
        for i, doc in enumerate(docs):
            console.print(Panel(doc.page_content[:500] + "...", title=f"Document {i+1} Preview"))
            console.print(f"Metadata: {doc.metadata}")
    except Exception as e:
        console.print(f"[red]Loader failed: {e}[/red]")
    finally:
        if conn: 
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass
        del manager

@app.command()
def splitter(text: str = typer.Option(None, "--text", help="Text to split"), 
             file_path: str = typer.Option(None, "--file", help="File to split")):
    """Test OracleTextSplitter."""
    if not text and not file_path:
        console.print("[red]Please provide --text or --file[/red]")
        raise typer.Exit(1)
        
    manager, client, conn = get_manager_and_conn()
    try:
        content = text
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        console.print(f"[cyan]Splitting text ({len(content)} chars) using OracleTextSplitter...[/cyan]")
        chunks = manager.split_text(text=content)
        console.print(f"[green]Generated {len(chunks)} chunks.[/green]")
        for i, chunk in enumerate(chunks[:3]):
            console.print(Panel(chunk, title=f"Chunk {i+1}"))
        if len(chunks) > 3:
            console.print(f"... and {len(chunks)-3} more.")
            
    except Exception as e:
        console.print(f"[red]Splitter failed: {e}[/red]")
    finally:
        if conn:
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass
        del manager

@app.command()
def summary(text: str):
    """Test OracleSummary."""
    manager, client, conn = get_manager_and_conn()
    try:
        console.print("[cyan]Generating summary using OracleSummary...[/cyan]")
        summary_text = manager.generate_summary(text)
        console.print(Panel(summary_text, title="Summary"))
    except Exception as e:
        console.print(f"[red]Summary generation failed: {e}[/red]")
    finally:
        if conn:
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass
        del manager

@app.command()
def embedding(text: str):
    """Test OracleEmbeddings."""
    manager, client, conn = get_manager_and_conn()
    try:
        console.print("[cyan]Generating embedding using OracleEmbeddings...[/cyan]")
        embeddings = manager.generate_embeddings([text])
        if embeddings and len(embeddings) > 0:
            vec = embeddings[0]
            console.print(f"[green]Generated embedding vector of dimension {len(vec)}[/green]")
            console.print(f"First 5 values: {vec[:5]}")
        else:
            console.print("[yellow]No embeddings returned.[/yellow]")
    except Exception as e:
        console.print(f"[red]Embedding generation failed: {e}[/red]")
    finally:
        if conn:
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass
        del manager

@app.command()
def all():
    """Run the comprehensive test suite for all features with sample data."""
    # Run the test suite script as a subprocess or import logic
    # Creating a dedicated test runner is cleaner
    console.print("[bold cyan]Running Oracle Feature Test Suite...[/bold cyan]")
    
    # We will invoke the test suite we are about to create
    test_suite_path = os.path.join(os.getcwd(), "tests", "test_oracle_features_suite.py")
    if not os.path.exists(test_suite_path):
         console.print(f"[red]Test suite not found at {test_suite_path}[/red]")
         raise typer.Exit(1)
         
    # run with python
    ret = os.system(f"{sys.executable} {test_suite_path}")
    if ret != 0:
        console.print("[red]Test suite failed.[/red]")
    else:
        console.print("[green]Test suite completed successfully.[/green]")

if __name__ == "__main__":
    app()
