"""Export commands for ragcli CLI."""

import typer
from rich import print as rprint
from ragcli.config.config_manager import load_config
# from ragcli.utils.metrics import get_session_metrics  # TODO
from typing import Optional

app = typer.Typer()

@app.command()
def export(
    logs: bool = typer.Option(True, "--logs", help="Export logs"),
    format: str = typer.Option("json", "--format", help="Output format (json, csv)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file")
):
    """Export logs or metrics."""
    config = load_config()
    
    if logs:
        # TODO: Read from log_file, export
        rprint("Exporting logs (stub)")
        if output:
            # Write to file
            with open(output, 'w') as f:
                f.write("Stub log data\n")
            rprint(f"Exported to {output}")
        else:
            rprint("Log data (stub): [INFO] Session started...")
    else:
        # Metrics
        metrics = get_session_metrics(config)  # TODO
        if format == "json":
            import json
            data = json.dumps(metrics, indent=2)
            if output:
                with open(output, 'w') as f:
                    f.write(data)
                rprint(f"Metrics exported to {output}")
            else:
                rprint(data)
        elif format == "csv":
            # Stub
            rprint("Metrics CSV (stub)")

if __name__ == "__main__":
    app()
