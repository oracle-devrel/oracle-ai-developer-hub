"""Upload commands for ragcli CLI."""

import typer
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
from rich.panel import Panel
from ragcli.core.rag_engine import upload_document_with_progress
from ragcli.config.config_manager import load_config
from typing import Optional

app = typer.Typer()
console = Console()

@app.command("add")
def add(
    file_path: Optional[str] = typer.Argument(None, help="Path to file or directory"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Upload directory recursively"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Upload document(s) to the vector store."""
    config = load_config()

    if file_path is None:
        from ragcli.utils.interactive import interactive_file_selector
        selected_path = interactive_file_selector()
        if selected_path is None:
            console.print("[yellow]Operation cancelled.[/yellow]")
            raise typer.Exit(0)
        file_path = str(selected_path)
    
    path = Path(file_path)
    if not path.exists():
        console.print("[red]File or directory not found.[/red]")
        raise typer.Exit(1)

    supported_formats = config['documents']['supported_formats']
    
    if path.is_dir() and recursive:
        # Walk directory, upload each file
        files = list(path.rglob("*"))
        files = [f for f in files if f.is_file() and f.suffix.lstrip('.') in supported_formats]
        
        if not files:
            console.print(f"[yellow]No supported documents found in directory.[/yellow]")
            console.print(f"Supported formats: [bold]{', '.join(supported_formats)}[/bold]")
            return

        
        console.print(f"   [bold #a855f7]Discovery:[/bold #a855f7] Identified [white]{len(files)}[/white] compatible document(s)\n")
        
        with Progress(
            SpinnerColumn(style="bold #a855f7"),
            TextColumn("   [progress.description]{task.description}"),
            BarColumn(bar_width=40, style="grey30", complete_style="#a855f7"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            overall_task = progress.add_task(f"[dim white]Orchestrating batch upload...[/dim white]", total=len(files))
            
            for file in files:
                try:
                    metadata = upload_document_with_progress(str(file), config, progress)
                    if verbose:
                        console.print(f"   [bold #4caf50]✓[/bold #4caf50] [dim]{file.name}[/dim]")
                except Exception as e:
                    console.print(f"   [bold red]✗[/bold red] [dim]{file.name}: {e}[/dim]")
                progress.advance(overall_task)
        
        console.print("\n   [bold #a855f7]Audit Complete:[/bold #a855f7] [white]Batch ingestion successful.[/white]")
        
    else:
        if path.is_dir():
            console.print("   [yellow]Recursive flag (-r) required for directory traversal.[/yellow]")
            raise typer.Exit(1)

        # Check if single file is supported
        if path.suffix.lstrip('.') not in supported_formats:
            console.print(f"[bold red]Error:[/bold red] File format '{path.suffix}' is not supported.")
            console.print(f"Supported formats: [bold]{', '.join(supported_formats)}[/bold]")
            console.print("See: https://docs.oracle.com/en/database/oracle/oracle-database/26/ccref/oracle-text-supported-document-formats.html")
            raise typer.Exit(1)
        
        try:
            with Progress(
                SpinnerColumn(style="bold #a855f7"),
                TextColumn("   [progress.description]{task.description}"),
                BarColumn(bar_width=40, style="grey30", complete_style="#a855f7"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                metadata = upload_document_with_progress(str(path), config, progress)
            
            # Show success summary
            summary = f"""
[dim white]Asset ID:[/dim white]      [#9333ea]{metadata['document_id']}[/#9333ea]
[dim white]Filename:[/dim white]      [white]{metadata['filename']}[/white]
[dim white]Format:[/dim white]        [#a855f7]{metadata['file_format'].upper()}[/#a855f7]
[dim white]Size:[/dim white]          [white]{metadata['file_size_bytes'] / 1024:.2f} KB[/white]
[dim white]Granularity:[/dim white]   [white]{metadata['chunk_count']} chunks[/white]
[dim white]Token Count:[/dim white]   [white]{metadata['total_tokens']}[/white]
[dim white]Latency:[/dim white]       [#a855f7]{metadata['upload_time_ms']:.0f} ms[/#a855f7]
            """
            console.print(Panel(
                summary.strip(), 
                title="[bold white]   Ingestion Audit Successful   [/bold white]", 
                border_style="#6b21a8",
                padding=(1, 2)
            ))
            
            if verbose:
                console.print("\n   [bold white]Extended Metadata:[/bold white]")
                for k, v in metadata.items():
                    console.print(f"      [dim white]{k}:[/dim white] [#a855f7]{v}[/#a855f7]")
                    
        except Exception as e:
            console.print(f"[bold red]✗ Upload failed:[/bold red] {e}")
            raise typer.Exit(1)

if __name__ == "__main__":
    app()
