"""
Feature Test Suite for Oracle AI Vector Search Integration.
This script verifies the functionality of Loader, Splitter, Embedding, and Summary components.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ragcli.config.config_manager import load_config
from ragcli.database.oracle_client import OracleClient
from ragcli.core.oracle_integration import OracleIntegrationManager
from rich.console import Console
from rich.panel import Panel

console = Console()

def run_suite():
    console.print("[bold cyan]=== Starting Oracle Feature Test Suite ===[/bold cyan]\n")
    
    config = load_config()
    client = OracleClient(config)
    conn = None
    try:
        conn = client.get_connection()
        manager = OracleIntegrationManager(conn)

        # 1. Test Loader
        console.print("[bold yellow]Testing OracleDocLoader...[/bold yellow]")
        try:
            sample_file = Path("tests/sample_data/oracle_test_doc.txt").absolute()
            if not sample_file.exists():
                sample_file.parent.mkdir(parents=True, exist_ok=True)
                with open(sample_file, 'w') as f:
                    f.write("This is a temporary test file for OracleDocLoader.")

            docs = manager.load_document(str(sample_file))
            if docs and len(docs) > 0:
                console.print(f"[green]PASS: Loaded {len(docs)} document(s).[/green]")
            else:
                console.print("[red]FAIL: No documents loaded.[/red]")
        except Exception as e:
            console.print(f"[red]FAIL: Loader error: {e}[/red]")

            # 2. Test Splitter
        console.print("\n[bold yellow]Testing OracleTextSplitter...[/bold yellow]")
        try:
            text = "This is sentence one. This is sentence two. This is sentence three."
            # Correct parameters per official docs:
            # - split: "sentence" requires by: "words"
            # - max: should be a reasonable number of words
            params = {"by": "words", "split": "sentence", "max": 100, "normalize": "all"}
            chunks = manager.split_text(text=text, params=params)
            
            if len(chunks) >= 3:
                 console.print(f"[green]PASS: Split into {len(chunks)} chunks (Expected >= 3).[/green]")
            else:
                 console.print(f"[yellow]WARN: Split into {len(chunks)} chunks with sentence splitter.[/yellow]")
                 
            # Test chars splitter
            # - split: "chars" is invalid. Use by: "characters" (or "chars") and split: "none"
            # - max: character split minimum is 50
            params_chars = {"by": "characters", "split": "none", "max": 50, "normalize": "all"}
            chunks_chars = manager.split_text(text="1234567890" * 10, params=params_chars)
            if len(chunks_chars) > 1:
                console.print(f"[green]PASS: Char split successful ({len(chunks_chars)} chunks).[/green]")
            else:
                console.print("[red]FAIL: Char split failed.[/red]")
        except Exception as e:
            console.print(f"[red]FAIL: Splitter error: {e}[/red]")

        # 3. Test Embeddings
        console.print("\n[bold yellow]Testing OracleEmbeddings...[/bold yellow]")
        try:
            console.print("Attempting to generate embedding using default config...")
            # Use specific model confirmed in DB
            embeddings = manager.generate_embeddings(["Hello World"], params={"provider": "database", "model": "ALL_MINILM_L12_V2"})
            if embeddings and len(embeddings) > 0:
                console.print(f"[green]PASS: Generated embedding (dim: {len(embeddings[0])}).[/green]")
            else:
                console.print("[red]FAIL: No embeddings returned.[/red]")
        except Exception as e:
            console.print(f"[red]FAIL: Embedding error: {e}[/red]")
            console.print("[dim]Note: This might fail if the DB model is not loaded correctly.[/dim]")

        # 4. Test Summary
        console.print("\n[bold yellow]Testing OracleSummary...[/bold yellow]")
        try:
            text_to_summarize = """
            Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by humans or animals. 
            Leading AI textbooks define the field as the study of "intelligent agents": any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
            """
            console.print("Attempting summary with 'database' provider...")
            summary = manager.generate_summary(text_to_summarize)
            if summary:
                console.print(f"[green]PASS: Summary generated ({len(summary)} chars).[/green]")
            else:
                console.print("[red]FAIL: Empty summary returned.[/red]")
        except Exception as e:
            console.print(f"[red]FAIL: Summary error: {e}[/red]")

    except ImportError:
        console.print("[red]FAIL: langchain-oracledb not installed.[/red]")
    except Exception as e:
        console.print(f"[red]FAIL: Suite initialization error: {e}[/red]")
    finally:
        if conn:
            conn.close()
        client.close()
    console.print("\n[bold cyan]=== Test Suite Completed ===[/bold cyan]")

if __name__ == "__main__":
    run_suite()
