"""Query commands for ragcli CLI."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from rich.prompt import Prompt
from ragcli.core.rag_engine import ask_query
from ragcli.config.config_manager import load_config
from typing import List, Optional

app = typer.Typer()
console = Console()

@app.command()
def ask(
    query: Optional[str] = typer.Argument(None, help="Question to ask"),
    docs: Optional[List[str]] = typer.Option(None, "--docs", help="Comma-separated document IDs"),
    top_k: Optional[int] = typer.Option(None, "--top-k", help="Number of top results"),
    threshold: Optional[float] = typer.Option(None, "--threshold", "-t", help="Min similarity score"),
    show_chain: bool = typer.Option(False, "--show-chain", "-c", help="Show retrieval chain"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose metrics")
):
    """Ask a question against the documents."""
    config = load_config()
    
    if query is None:
        query = Prompt.ask("Enter your question")

    document_ids = docs.split(',') if docs else None
    
    try:
        result = ask_query(query, document_ids, top_k, threshold, config)
        
        # Premium Response Presentation
        console.print("\n   [bold #a855f7]R E S P O N S E[/bold #a855f7]")
        console.print(Panel(
            result['response'],
            border_style="#6b21a8",
            padding=(1, 2),
            subtitle="[dim white]Source: Contextual Intelligence Layer[/dim white]"
        ))
        
        # Results
        if show_chain or verbose:
            console.print("\n   [bold #a855f7]R E T R I E V A L   C H A I N[/bold #a855f7]")
            table = Table(
                show_header=True,
                box=None,
                header_style="bold #a855f7",
                title_style="bold white",
                padding=(0, 2)
            )
            table.add_column("Asset ID", style="dim white")
            table.add_column("Chunk", justify="right", style="#9333ea")
            table.add_column("Score", justify="right", style="#4caf50")
            table.add_column("Snippet", style="italic white")
            
            for r in result['results']:
                display_id = r['document_id'][:8] + "..."
                table.add_row(
                    display_id,
                    str(r['chunk_number']),
                    f"{r['similarity_score']:.3f}",
                    r['text'][:100].replace("\n", " ") + "..."
                )
            console.print(table)
        
        # Metrics
        if verbose:
            console.print("\n   [bold white]Operational Metrics[/bold white]")
            for k, v in result['metrics'].items():
                console.print(f"      [dim white]{k}:[/dim white] [#a855f7]{v}[/#a855f7]")
                
    except Exception as e:
        rprint(typer.style(f"Query failed: {e}", fg=typer.colors.RED))
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
