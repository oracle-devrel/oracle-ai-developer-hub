"""Main entry point for ragcli CLI."""

import sys
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich import print as rprint
from .commands.config import config_app
from .commands.upload import app as upload_app
from .commands.query import app as query_app
from .commands.documents import app as documents_app
from .commands.visualize import app as visualize_app
from .commands.export import app as export_app
from .commands.db import app as db_app
from .commands.status import app as status_app
from .commands.status import app as status_app
from .commands.models import app as models_app
from .commands.oracle_test import app as oracle_test_app
from .commands.eval_cmd import app as eval_app
from .commands.sync_cmd import app as sync_app
from ..config.config_manager import load_config

# Import commands for direct execution
from .commands.upload import add as upload_cmd
from .commands.query import ask as ask_cmd
from .commands.documents import list_docs, delete as delete_doc
from .commands.visualize import visualize as visualize_cmd
from .commands.db import init as db_init, browse as db_browse, query as db_query, stats as db_stats

app = typer.Typer()
console = Console()

app.add_typer(config_app, name="config")
app.add_typer(documents_app, name="docs")
app.add_typer(visualize_app, name="visualize")
app.add_typer(export_app, name="export")
app.add_typer(db_app, name="db")
app.add_typer(models_app, name="models")
app.add_typer(oracle_test_app, name="oracle-test")
app.add_typer(eval_app, name="eval")
app.add_typer(sync_app, name="sync")

# Expose commands directly
from .commands.upload import add as upload_cmd
from .commands.query import ask as ask_cmd
from .commands.status import status as status_cmd

app.command(name="upload")(upload_cmd)
app.command(name="ask")(ask_cmd)
app.command(name="status")(status_cmd)

@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload")
):
    """Launch the FastAPI server for AnythingLLM integration."""
    from ragcli.api.server import start_server
    console.print(f"[cyan]Starting ragcli API server on {host}:{port}[/cyan]")
    console.print(f"[cyan]API docs available at: http://{host}:{port}/docs[/cyan]")
    start_server(host=host, port=port, reload=reload)

@app.command()
def init_db():
    """Alias for db init."""
    from .commands.db import init
    init()

import questionary
from questionary import Style

# Premium Gemini-style color palette
GEMINI_STYLE = Style([
    ('qmark', 'fg:#673ab7 bold'),       # question mark color
    ('question', 'bold'),               # question text
    ('answer', 'fg:#2196f3 bold'),      # submitted answer color
    ('pointer', 'fg:#673ab7 bold'),     # pointer color
    ('highlighted', 'fg:#673ab7 bold'), # highlighted element color
    ('selected', 'fg:#4caf50'),         # selected element (in check)
    ('separator', 'fg:#cc5454'),        # separator color
    ('instruction', 'italic'),          # instruction text
    ('text', 'fg:#ffffff'),             # plain text
    ('disabled', 'fg:#858585 italic')  # disabled element color
])

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    config = load_config()
    version = config.get('app', {}).get('version', '1.0.0')

    # Premium Gemini-style header

    header_content = f"""
[bold #a855f7]r[/bold #a855f7][bold #9333ea]a[/bold #9333ea][bold #7e22ce]g[/bold #7e22ce][bold #6b21a8]c[/bold #6b21a8][bold #581c87]l[/bold #581c87][bold #4c1d95]i[/bold #4c1d95] [dim bold grey50]Command Center[/]
    """

    console.print(Panel(
        header_content.strip(),
        style="bold white",
        border_style="#6b21a8",
        padding=(1, 4),
        subtitle=f"[dim]RAG Orchestration Layer v{version}[/dim]"
    ))
    console.print(f"[dim grey50]  Current Context: {os.getcwd()}[/]\n")

def menu_documents():
    while True:
        print_header()

        choices = [
            {"name": "List all documents", "value": "1"},
            {"name": "Delete a document", "value": "2"},
            questionary.Separator(),
            {"name": "Main Menu", "value": "0"}
        ]

        choice = questionary.select(
            "   Document Intelligence",
            choices=choices,
            style=GEMINI_STYLE,
            use_arrow_keys=True,
            pointer="›"
        ).ask()

        if not choice or choice == "0":
            return
        elif choice == "1":
            list_docs(format="table", verbose=False)
            input("\n   [Press Enter to return]")
        elif choice == "2":
            doc_id = Prompt.ask("   Enter Document ID to purge")
            if Confirm.ask(f"   Confirm destruction of {doc_id}?", default=False):
                try:
                    delete_doc(doc_id)
                except Exception as e:
                    console.print(f"   [red]Failure: {e}[/red]")
            input("\n   [Press Enter to return]")

def menu_db():
    while True:
        print_header()

        choices = [
            {"name": "Initialize Core Schema (Schemas & Indices)", "value": "1"},
            {"name": "Insight: Browse Tables", "value": "2"},
            {"name": "Direct Access: SQL Query", "value": "3"},
            {"name": "Analytics: Resource Statistics", "value": "4"},
            questionary.Separator(),
            {"name": "Main Menu", "value": "0"}
        ]

        choice = questionary.select(
            "   Database Autonomy",
            choices=choices,
            style=GEMINI_STYLE,
            use_arrow_keys=True,
            pointer="›"
        ).ask()

        if not choice or choice == "0":
            return
        elif choice == "1":
            if Confirm.ask("   This will re-initialize core schemas. Continue?", default=True):
                try:
                    db_init()
                except Exception as e:
                    console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "2":
            table = questionary.select(
                "   Select target table",
                choices=["DOCUMENTS", "CHUNKS", "QUERIES"],
                style=GEMINI_STYLE,
                default="DOCUMENTS"
            ).ask()
            limit = IntPrompt.ask("   Row limit", default=20)
            try:
                db_browse(table=table, limit=limit, offset=0)
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "3":
            sql = Prompt.ask("   SQL Input")
            try:
                db_query(sql=sql, format="table")
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "4":
            try:
                db_stats()
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")

def menu_visualize():
    from .commands.visualize import visual_query as visual_query_cmd
    print_header()
    console.print("   [bold #a855f7]Visual Analytics[/bold #a855f7]")

    choices = [
        {"name": "Chain Visualization (Tokenization + Embedding)", "value": "1"},
        {"name": "Visual Query (Similarity Search)", "value": "2"},
        questionary.Separator(),
        {"name": "Main Menu", "value": "0"}
    ]

    choice = questionary.select(
        "   Select visualization type:",
        choices=choices,
        style=GEMINI_STYLE,
        use_arrow_keys=True,
        pointer="›"
    ).ask()

    if not choice or choice == "0":
        return
    elif choice == "1":
        query = Prompt.ask("   Enter text to visualize")
        try:
            visualize_cmd(query=query, type="chain")
        except Exception as e:
            console.print(f"   [red]Error: {e}[/red]")
        input("\n   [Press Enter to return]")
    elif choice == "2":
        query = Prompt.ask("   Enter query for similarity search")
        try:
            visual_query_cmd(query=query, top_k=5)
        except Exception as e:
            console.print(f"   [red]Error: {e}[/red]")
        input("\n   [Press Enter to return]")


def run_repl():
    """Run the interactive mode with premium Gemini-style UI."""
    while True:
        print_header()

        choices = [
            {"name": "Ingest: Document Upload", "value": "1"},
            {"name": "Inquiry: Contextual Ask", "value": "2"},
            {"name": "Knowledge: Manage Assets", "value": "3"},
            {"name": "Insight: Chain Visualization", "value": "4"},
            {"name": "Authority: DB Orchestration", "value": "5"},
            {"name": "Health: System Status", "value": "6"},
            {"name": "Audit: Integration Tests", "value": "7"},
            questionary.Separator(),
            {"name": "Terminate Session", "value": "0"}
        ]

        choice = questionary.select(
            "   Select Objective:",
            choices=choices,
            style=GEMINI_STYLE,
            use_arrow_keys=True,
            pointer="›"
        ).ask()

        try:
            if not choice or choice == "0":
                console.print("\n   [bold #a855f7]Session terminated. Farewell.[/bold #a855f7]")
                break
            elif choice == "1":
                # Interactive upload
                upload_cmd(file_path=None, recursive=False, verbose=True)
                input("\n   [Press Enter to return]")
            elif choice == "2":
                # Interactive query
                ask_cmd(query=None, docs=None, top_k=None, threshold=None, show_chain=False, verbose=False)
                input("\n   [Press Enter to return]")
            elif choice == "3":
                menu_documents()
            elif choice == "4":
                menu_visualize()
            elif choice == "5":
                menu_db()
            elif choice == "6":
                status_cmd()
                input("\n   [Press Enter to return]")
            elif choice == "7":
                menu_oracle_tests()

        except Exception as e:
            console.print(f"\n   [bold red]Critical Anomaly Detected:[/bold red] {e}")
            input("\n   [Press Enter to return]")

def menu_oracle_tests():
    from .commands.oracle_test import loader, splitter, summary, embedding, all as test_all

    while True:
        print_header()

        choices = [
            {"name": "Verify: Document Loader", "value": "1"},
            {"name": "Verify: Text Splitter", "value": "2"},
            {"name": "Verify: Summarization Engine", "value": "3"},
            {"name": "Verify: Embedding Pipeline", "value": "4"},
            {"name": "Full Integrity Audit (Sample Suite)", "value": "5"},
            questionary.Separator(),
            {"name": "Main Menu", "value": "0"}
        ]

        choice = questionary.select(
            "   Oracle AI Integration Testing",
            choices=choices,
            style=GEMINI_STYLE,
            use_arrow_keys=True,
            pointer="›"
        ).ask()

        if not choice or choice == "0":
            return
        elif choice == "1":
            file_path = Prompt.ask("   Source document path")
            try:
                loader(file_path=file_path)
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "2":
            text_input = Prompt.ask("   Input text or path")
            # check if it is a file
            if os.path.exists(text_input):
                 try:
                    splitter(text=None, file_path=text_input)
                 except Exception as e:
                    console.print(f"   [red]Error: {e}[/red]")
            else:
                 try:
                    splitter(text=text_input, file_path=None)
                 except Exception as e:
                    console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "3":
            text = Prompt.ask("   Target summary text")
            try:
                summary(text=text)
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "4":
            text = Prompt.ask("   Sample text for vectorization")
            try:
                embedding(text=text)
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")
        elif choice == "5":
            try:
                test_all()
            except Exception as e:
                console.print(f"   [red]Error: {e}[/red]")
            input("\n   [Press Enter to return]")

def main():
    """Compatibility entry point."""
    if len(sys.argv) == 1:
        try:
            run_repl()
        except KeyboardInterrupt:
            sys.exit(0)
    else:
        app()

if __name__ == "__main__":
    main()
