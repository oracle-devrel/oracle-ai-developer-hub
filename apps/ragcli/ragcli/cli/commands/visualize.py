"""Visualization commands for ragcli CLI."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from ragcli.core.oracle_integration import OracleIntegrationManager
from typing import Optional

app = typer.Typer()
console = Console()


@app.command()
def visualize(
    query: Optional[str] = None,
    type: str = typer.Option("chain", "--type", "-t", help="Visualization type (chain, embedding)")
):
    """Visualize text tokenization and embedding using Oracle AI."""
    config = load_config()
    
    if not query:
        rprint("[yellow]Provide text to visualize with --query or enter it below.[/yellow]")
        query = console.input("   Enter text: ")
        if not query:
            rprint("[red]No input provided.[/red]")
            raise typer.Exit(1)

    client = OracleClient(config)
    conn = None
    
    try:
        conn = client.get_connection()
        manager = OracleIntegrationManager(conn)
        
        # Step 1: Chunking with OracleTextSplitter
        console.print("\n[bold cyan]═══ Tokenization (OracleTextSplitter) ═══[/bold cyan]")
        
        # Use sentence-based splitting for visualization
        split_params = {"by": "words", "split": "sentence", "max": 100, "normalize": "all"}
        chunks = manager.split_text(text=query, params=split_params)
        
        if not chunks:
            console.print("[yellow]No chunks generated from input.[/yellow]")
            return
        
        chunk_table = Table(show_header=True, header_style="bold #a855f7", box=None)
        chunk_table.add_column("#", style="dim", width=4)
        chunk_table.add_column("Chunk Content", style="white", no_wrap=False)
        chunk_table.add_column("Length", style="cyan", justify="right")
        
        for i, chunk in enumerate(chunks, 1):
            chunk_table.add_row(str(i), chunk, f"{len(chunk)} chars")
        
        console.print(chunk_table)
        console.print(f"\n   [dim]Total chunks: {len(chunks)}[/dim]")
        
        # Step 2: Embeddings with OracleEmbeddings
        console.print("\n[bold cyan]═══ Embeddings (OracleEmbeddings) ═══[/bold cyan]")
        
        embed_params = {"provider": "database", "model": "ALL_MINILM_L12_V2"}
        embeddings = manager.generate_embeddings(chunks, params=embed_params)
        
        if embeddings and len(embeddings) > 0:
            dim = len(embeddings[0])
            console.print(f"   [bold]Model:[/bold] ALL_MINILM_L12_V2 | [bold]Dimension:[/bold] {dim}")
            
            embed_table = Table(show_header=True, header_style="bold #a855f7", box=None)
            embed_table.add_column("Chunk", style="dim", width=8)
            embed_table.add_column("Vector Preview (first 5 values)", style="white")
            
            for i, vec in enumerate(embeddings, 1):
                preview_vals = ", ".join([f"{v:.4f}" for v in vec[:5]])
                embed_table.add_row(f"Chunk {i}", f"[{preview_vals}, ...]")
            
            console.print(embed_table)
        else:
            console.print("[yellow]No embeddings generated.[/yellow]")
        
        console.print("\n[bold green]Visualization complete.[/bold green]")
        
    except ImportError:
        console.print("[red]langchain-oracledb is required for Oracle AI visualization.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Visualization error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if conn:
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass


@app.command()
def visual_query(
    query: Optional[str] = None,
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of closest results")
):
    """Visualize similarity search results against stored documents."""
    from ragcli.database.vector_ops import search_similar
    
    config = load_config()
    
    if not query:
        query = console.input("   Enter query text: ")
        if not query:
            rprint("[red]No input provided.[/red]")
            raise typer.Exit(1)

    client = OracleClient(config)
    conn = None
    
    try:
        conn = client.get_connection()
        
        # Step 1: Generate query embedding using the SAME model as documents
        # Documents use Ollama's nomic-embed-text (768 dims), not Oracle's model
        from ragcli.core.embedding import generate_embedding
        
        console.print("\n[bold cyan]═══ Query Embedding ═══[/bold cyan]")
        embedding_model = config['ollama']['embedding_model']  # nomic-embed-text
        query_vec = generate_embedding(query, embedding_model, config, conn=conn)
        
        if not query_vec:
            console.print("[red]Failed to generate query embedding.[/red]")
            raise typer.Exit(1)
        
        console.print(f"   [bold]Query:[/bold] \"{query}\"")
        console.print(f"   [bold]Model:[/bold] {embedding_model}")
        console.print(f"   [bold]Dimension:[/bold] {len(query_vec)}")
        preview_vals = ", ".join([f"{v:.4f}" for v in query_vec[:5]])
        console.print(f"   [bold]Vector:[/bold] [{preview_vals}, ...]")
        
        # Step 2: Similarity search
        console.print("\n[bold cyan]═══ Closest Vectors (Similarity Search) ═══[/bold cyan]")
        results = search_similar(conn, query_vec, top_k=top_k, min_similarity=0.0)
        
        if not results:
            console.print("[yellow]No similar chunks found in the database.[/yellow]")
            console.print("[dim]Tip: Upload documents first using 'Ingest: Document Upload'.[/dim]")
        else:
            console.print(f"   [dim]Found {len(results)} matches (ordered by similarity)[/dim]\n")
            
            result_table = Table(show_header=True, header_style="bold #a855f7", box=None)
            result_table.add_column("Rank", style="dim", width=5)
            result_table.add_column("Score", style="cyan", width=8)
            result_table.add_column("Document", style="white", width=12)
            result_table.add_column("Chunk Content", style="white", no_wrap=False)
            
            for i, res in enumerate(results, 1):
                score_str = f"{res['similarity_score']:.4f}"
                doc_short = res['document_id'][:8] + "..."
                text_preview = res['text'][:100] + "..." if len(res['text']) > 100 else res['text']
                result_table.add_row(f"#{i}", score_str, doc_short, text_preview)
            
            console.print(result_table)
            
            # Show embedding comparison for top result
            if results[0].get('embedding'):
                console.print("\n[bold cyan]═══ Top Match Vector Comparison ═══[/bold cyan]")
                top_emb = results[0]['embedding']
                top_preview = ", ".join([f"{v:.4f}" for v in top_emb[:5]])
                console.print(f"   [bold]Query Vector:[/bold] [{preview_vals}, ...]")
                console.print(f"   [bold]Match Vector:[/bold] [{top_preview}, ...]")
                console.print(f"   [bold]Similarity:[/bold] {results[0]['similarity_score']:.4f}")
        
        console.print("\n[bold green]Visual query complete.[/bold green]")
        
    except ImportError:
        console.print("[red]langchain-oracledb is required for Oracle AI visualization.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Visual query error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        if conn:
            try: conn.close()
            except: pass
        if client:
            try: client.close()
            except: pass


if __name__ == "__main__":
    app()
