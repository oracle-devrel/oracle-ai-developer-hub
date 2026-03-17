"""Model management commands for ragcli CLI."""

import typer
from rich import print as rprint
from rich.table import Table
from rich.console import Console
from ragcli.core.ollama_manager import (
    list_available_models,
    get_embedding_models,
    get_chat_models,
    validate_config_models,
    validate_model
)
from ragcli.config.config_manager import load_config

app = typer.Typer()
console = Console()


@app.command("list")
def list_models(
    type: str = typer.Option(None, "--type", "-t", help="Filter by type: embedding, chat, or all")
):
    """List available Ollama models."""
    config = load_config()
    
    if type == "embedding":
        models = get_embedding_models(config)
        title = "Available Embedding Models"
    elif type == "chat":
        models = get_chat_models(config)
        title = "Available Chat Models"
    else:
        # Show all with categorization
        all_models = list_available_models(config)
        
        table = Table(title="Available Ollama Models")
        table.add_column("Model Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Size", style="yellow")
        table.add_column("Modified", style="green")
        
        for model in all_models.get('models', []):
            name = model['name']
            size_gb = model.get('size', 0) / (1024**3)
            modified = model.get('modified_at', 'N/A')[:19]  # Truncate timestamp
            
            # Determine type
            if 'embed' in name.lower():
                model_type = "Embedding"
            else:
                model_type = "Chat/LLM"
            
            table.add_row(
                name,
                model_type,
                f"{size_gb:.2f} GB",
                modified
            )
        
        console.print(table)
        
        # Show current config
        console.print("\n[bold]Current Configuration:[/bold]")
        console.print(f"  Embedding Model: [cyan]{config['ollama']['embedding_model']}[/cyan]")
        console.print(f"  Chat Model: [cyan]{config['ollama']['chat_model']}[/cyan]")
        return
    
    # Simple list for filtered types
    if models:
        console.print(f"\n[bold]{title}:[/bold]")
        for model in models:
            console.print(f"  • {model}")
    else:
        console.print(f"[yellow]No {type} models found in Ollama[/yellow]")


@app.command("validate")
def validate_models():
    """Validate configured models exist in Ollama."""
    config = load_config()
    
    console.print("[bold]Validating configured models...[/bold]\n")
    
    results = validate_config_models(config)
    
    # Embedding model
    if results['embedding_model_valid']:
        console.print(f"✓ Embedding model '[cyan]{config['ollama']['embedding_model']}[/cyan]' is available")
    else:
        console.print(f"✗ Embedding model '[red]{config['ollama']['embedding_model']}[/red]' not found")
        if 'embedding_model' in results['suggestions']:
            console.print(f"  → Suggestion: Use '[green]{results['suggestions']['embedding_model']}[/green]'")
    
    # Chat model
    if results['chat_model_valid']:
        console.print(f"✓ Chat model '[cyan]{config['ollama']['chat_model']}[/cyan]' is available")
    else:
        console.print(f"✗ Chat model '[red]{config['ollama']['chat_model']}[/red]' not found")
        if 'chat_model' in results['suggestions']:
            console.print(f"  → Suggestion: Use '[green]{results['suggestions']['chat_model']}[/green]'")
    
    # Warnings
    if results['warnings']:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in results['warnings']:
            console.print(f"  ! {warning}")
    
    # Overall status
    if results['embedding_model_valid'] and results['chat_model_valid']:
        console.print("\n[bold green]All models validated successfully![/bold green]")
    else:
        console.print("\n[bold yellow]Some models need attention. Update config.yaml or pull models with 'ollama pull <model>'[/bold yellow]")


@app.command("check")
def check_model(model_name: str):
    """Check if a specific model is available."""
    config = load_config()
    
    if validate_model(model_name, config):
        console.print(f"✓ Model '[green]{model_name}[/green]' is available in Ollama")
    else:
        console.print(f"✗ Model '[red]{model_name}[/red]' not found in Ollama")
        console.print(f"\nTo install: [cyan]ollama pull {model_name}[/cyan]")


if __name__ == "__main__":
    app()

