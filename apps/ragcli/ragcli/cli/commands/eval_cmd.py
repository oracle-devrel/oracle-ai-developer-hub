"""CLI commands for RAG evaluation suite."""

import typer
from rich.console import Console
from rich.table import Table

from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="RAG evaluation suite")
console = Console()


@app.command()
def synthetic(
    document_id: str = typer.Option(None, "--doc", help="Evaluate specific document"),
):
    """Generate synthetic Q&A pairs and run evaluation."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.eval.runner import EvalRunner
        runner = EvalRunner(conn, config)

        console.print("[cyan]Starting synthetic evaluation...[/]")
        run_id = runner.create_run("synthetic")
        console.print(f"[green]Created eval run:[/] {run_id}")

        # Note: Full synthetic evaluation requires generate + run pipeline
        # which needs the RAG engine to be running. For now, just create the run.
        console.print("[yellow]Run created. Use API to trigger full evaluation pipeline.[/]")
    except Exception as e:
        console.print(f"[red]Evaluation failed: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def replay():
    """Re-run past queries through current pipeline."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.eval.runner import EvalRunner
        runner = EvalRunner(conn, config)

        console.print("[cyan]Starting replay evaluation...[/]")
        run_id = runner.create_run("replay")
        console.print(f"[green]Created replay run:[/] {run_id}")
        console.print("[yellow]Replay scoring requires pipeline execution. Use API for full replay.[/]")
    except Exception as e:
        console.print(f"[red]Replay failed: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def report(
    run_id: str = typer.Argument(None, help="Specific run ID (latest if omitted)"),
):
    """Display evaluation report."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.eval.runner import EvalRunner
        from ragcli.eval.reporter import EvalReporter

        runner = EvalRunner(conn, config)
        reporter = EvalReporter(conn)

        if run_id is None:
            runs = runner.list_runs(limit=1)
            if not runs:
                console.print("[yellow]No evaluation runs found.[/]")
                raise typer.Exit(0)
            run_id = runs[0]['run_id']

        report_data = reporter.generate_report(run_id)
        text = reporter.format_report_text(report_data)
        console.print(text)
    except Exception as e:
        console.print(f"[red]Report failed: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()


@app.command()
def runs(
    limit: int = typer.Option(10, "--limit", help="Max runs to show"),
):
    """List evaluation runs."""
    config = load_config()
    client = OracleClient(config)
    conn = client.get_connection()
    try:
        from ragcli.eval.runner import EvalRunner
        runner = EvalRunner(conn, config)

        run_list = runner.list_runs(limit=limit)
        if not run_list:
            console.print("[yellow]No evaluation runs found.[/]")
            raise typer.Exit(0)

        table = Table(title="Evaluation Runs")
        table.add_column("Run ID", style="cyan", max_width=12)
        table.add_column("Mode")
        table.add_column("Pairs", justify="right")
        table.add_column("Faith.", justify="right")
        table.add_column("Relev.", justify="right")
        table.add_column("Prec.", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("Started")

        for r in run_list:
            table.add_row(
                r['run_id'][:12],
                r.get('eval_mode', ''),
                str(r.get('total_pairs', 0)),
                f"{r['avg_faithfulness']:.2f}" if r.get('avg_faithfulness') else "-",
                f"{r['avg_relevance']:.2f}" if r.get('avg_relevance') else "-",
                f"{r['avg_context_precision']:.2f}" if r.get('avg_context_precision') else "-",
                f"{r['avg_context_recall']:.2f}" if r.get('avg_context_recall') else "-",
                str(r.get('started_at', ''))[:19],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to list runs: {e}[/]")
        raise typer.Exit(1)
    finally:
        conn.close()
        client.close()
