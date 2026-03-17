"""Configuration commands for ragcli CLI."""

import typer
from pathlib import Path
from ragcli.config.config_manager import load_config

config_app = typer.Typer()

@config_app.command()
def init():
    """Initialize config.yaml from example if not exists."""
    config_path = Path("config.yaml")
    example_path = Path("config.yaml.example")
    if not config_path.exists():
        config_path.write_text(example_path.read_text())
        typer.echo("Created config.yaml from example. Please edit it with your settings.")
    else:
        typer.echo("config.yaml already exists.")

@config_app.command()
def show():
    """Show current configuration (sensitive fields masked)."""
    config = load_config()
    # Mask sensitive
    config["oracle"]["password"] = "******" if config["oracle"]["password"] else ""
    typer.echo(typer.style("Current Configuration:", bold=True))
    for section, values in config.items():
        typer.echo(f"\n{section.upper()}:")
        for k, v in values.items():
            typer.echo(f"  {k}: {v}")

if __name__ == "__main__":
    config_app()
