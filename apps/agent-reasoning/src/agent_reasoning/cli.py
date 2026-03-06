#!/usr/bin/env python3
"""Interactive CLI for Agent Reasoning."""
import os
import sys
import time
import subprocess

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown

import requests

from agent_reasoning.interceptor import ReasoningInterceptor, AGENT_MAP
from agent_reasoning.visualization import get_visualizer
from agent_reasoning.config import get_ollama_host, set_ollama_host, get_config_file, load_config

console = Console()

MODEL_NAME = "gemma3:latest"

# Initialize client (uses config file automatically)
client = ReasoningInterceptor()


def get_ollama_models():
    """Get list of available Ollama models."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = [line.split()[0] for line in lines if line.strip()]
        return models
    except Exception:
        return ["gemma3:latest", "gemma3:270m", "llama3"]


def select_model_panel():
    """Interactive model selection."""
    global MODEL_NAME
    models = get_ollama_models()

    selected = questionary.select(
        "Select AI Model:",
        choices=models,
        default=MODEL_NAME
    ).ask()

    if selected:
        MODEL_NAME = selected
        console.print(f"[green]Model set to: {MODEL_NAME}[/green]")


def configure_endpoint():
    """Configure the Ollama API endpoint."""
    global client
    
    current_host = get_ollama_host()
    
    console.print(f"\n[dim]Current endpoint: {current_host}[/dim]")
    console.print(f"[dim]Config file: {get_config_file()}[/dim]")
    console.print("[dim]Enter a new endpoint URL (e.g., http://192.168.1.100:11434)[/dim]")
    console.print("[dim]Press Enter to keep current, or type 'reset' for localhost[/dim]\n")
    
    new_endpoint = Prompt.ask("Ollama API Endpoint", default=current_host)
    
    if new_endpoint.lower() == 'reset':
        new_endpoint = "http://localhost:11434"
    
    if new_endpoint and new_endpoint != current_host:
        # Save to config file
        set_ollama_host(new_endpoint)
        # Recreate client with new endpoint
        client = ReasoningInterceptor(host=new_endpoint)
        console.print(f"[green]Endpoint set to: {new_endpoint}[/green]")
        console.print(f"[dim]Saved to: {get_config_file()}[/dim]")
    else:
        console.print(f"[yellow]Endpoint unchanged: {current_host}[/yellow]")


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print CLI header."""
    clear_screen()
    console.print(Panel.fit(
        "[bold cyan]AGENT REASONING CLI[/bold cyan]\n[dim]Advanced Cognitive Architectures[/dim]",
        border_style="cyan"
    ))
    console.print(f"[dim]Working Directory: {os.getcwd()}[/dim]\n")


def run_with_visualizer(strategy, query, visualizer):
    """Run agent with rich visualization using structured events."""
    agent_class = AGENT_MAP.get(strategy)
    if not agent_class:
        console.print(f"[red]Unknown strategy: {strategy}[/red]")
        return

    agent = agent_class(model=MODEL_NAME)

    if not hasattr(agent, 'stream_structured'):
        console.print("[dim]Agent does not support structured streaming, falling back to text mode.[/dim]")
        run_with_markdown(strategy, query)
        return

    try:
        with Live(visualizer.render(), refresh_per_second=10, vertical_overflow="visible") as live:
            for event in agent.stream_structured(query):
                visualizer.update(event)
                live.update(visualizer.render())
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def run_with_markdown(strategy, query):
    """Fallback: Run agent with simple markdown rendering."""
    full_model_name = f"{MODEL_NAME}+{strategy}"
    full_response = ""

    with Live("", refresh_per_second=10, vertical_overflow="visible") as live:
        try:
            for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                chunk = chunk_dict.get("response", "")
                full_response += chunk
                live.update(Markdown(full_response))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def run_agent_chat(strategy):
    """Run interactive chat with a specific agent strategy."""
    print_header()
    console.print(f"[bold yellow]Chat Mode: {strategy.upper()}[/bold yellow]")
    console.print("Type 'exit' or '0' to return.")

    while True:
        query = Prompt.ask("\n[bold green]Query[/bold green]")
        if query.lower() in ['exit', 'quit', '0']:
            break

        full_model_name = f"{MODEL_NAME}+{strategy}"
        console.print(f"[dim]Using model: {full_model_name}[/dim]")
        console.print(f"[bold cyan]--- {strategy.upper()} Thinking ---[/bold cyan]")

        visualizer = get_visualizer(strategy)

        if visualizer:
            run_with_visualizer(strategy, query, visualizer)
        else:
            run_with_markdown(strategy, query)


def run_arena_mode():
    """Run the same query across all agents to compare."""
    print_header()
    console.print("[bold yellow]ARENA MODE[/bold yellow]")
    console.print("Run the same query across ALL agents to compare reasoning styles.")

    query = Prompt.ask("\n[bold green]Enter Test Query[/bold green]")
    if not query:
        return

    strategies = ["standard", "cot", "tot", "react", "recursive", "reflection",
                  "decomposed", "least_to_most", "consistency"]

    results = {}

    for strategy in strategies:
        console.print(f"\n[bold magenta]Running {strategy.upper()}...[/bold magenta]")
        full_model_name = f"{MODEL_NAME}+{strategy}"

        start_time = time.time()
        response_text = ""

        console.rule(f"[bold]{strategy}[/bold]")

        try:
            with Live("", refresh_per_second=10, vertical_overflow="visible") as live:
                for chunk_dict in client.generate(model=full_model_name, prompt=query, stream=True):
                    chunk = chunk_dict.get("response", "")
                    response_text += chunk
                    live.update(Markdown(response_text))

        except Exception as e:
            response_text = f"Error: {e}"
            console.print(f"[red]{e}[/red]")

        duration = time.time() - start_time
        results[strategy] = (response_text, duration)
        console.print(f"\n[green]Done in {duration:.2f}s[/green]")

    # Summary Table
    console.print("\n\n")
    console.rule("[bold red]Comparison Results[/bold red]")

    table = Table(title="Arena Results")
    table.add_column("Strategy", style="cyan")
    table.add_column("Time", style="green")
    table.add_column("Response Length", style="magenta")

    for strat, (resp, dur) in results.items():
        table.add_row(strat, f"{dur:.2f}s", str(len(resp)))

    console.print(table)

    if Confirm.ask("Save Arena Report?"):
        with open("arena_report.md", "w") as f:
            f.write(f"# Arena Report\n**Model**: {MODEL_NAME}\n**Query**: {query}\n\n")
            for strat, (resp, dur) in results.items():
                f.write(f"## {strat.upper()} ({dur:.2f}s)\n{resp}\n\n")
        console.print("[green]Saved to arena_report.md[/green]")


def main_menu():
    """Main interactive menu."""
    while True:
        clear_screen()
        print_header()

        choices = [
            questionary.Choice("Chat with Standard Agent", value="1"),
            questionary.Choice("Chain of Thought (CoT)", value="2"),
            questionary.Choice("Tree of Thoughts (ToT)", value="3"),
            questionary.Choice("ReAct (Tools + Web)", value="4"),
            questionary.Choice("Recursive (RLM)", value="5"),
            questionary.Choice("Self-Reflection", value="6"),
            questionary.Choice("Decomposed Prompting", value="7"),
            questionary.Choice("Least-to-Most", value="8"),
            questionary.Choice("Self-Consistency", value="9"),
            questionary.Separator(),
            questionary.Choice("ARENA: Run All Compare", value="a"),
            questionary.Choice(f"Select AI Model (Current: {MODEL_NAME})", value="m"),
            questionary.Choice(f"Configure Endpoint ({get_ollama_host()})", value="e"),
            questionary.Separator(),
            questionary.Choice("Exit", value="0")
        ]

        choice = questionary.select(
            "Select an Activity:",
            choices=choices,
            use_arrow_keys=True
        ).ask()

        if not choice or choice == "0":
            sys.exit(0)
        elif choice == "m":
            select_model_panel()
        elif choice == "e":
            configure_endpoint()
        elif choice == "1":
            run_agent_chat("standard")
        elif choice == "2":
            run_agent_chat("cot")
        elif choice == "3":
            run_agent_chat("tot")
        elif choice == "4":
            run_agent_chat("react")
        elif choice == "5":
            run_agent_chat("recursive")
        elif choice == "6":
            run_agent_chat("reflection")
        elif choice == "7":
            run_agent_chat("decomposed")
        elif choice == "8":
            run_agent_chat("least_to_most")
        elif choice == "9":
            run_agent_chat("consistency")
        elif choice == "a":
            run_arena_mode()



def check_ollama_config():
    """Check if Ollama host is configured and reachable."""
    config_file = get_config_file()
    ollama_host = get_ollama_host()
    
    # Check if config file exists
    if not config_file.exists():
        console.print(Panel(
            f"[yellow]Config file not found at:[/yellow]\n{config_file}\n\n"
            f"[dim]Using default: {ollama_host}[/dim]\n\n"
            "You can configure the endpoint from the main menu.",
            title="[yellow]Configuration[/yellow]",
            border_style="yellow"
        ))
    else:
        console.print(f"[dim]Config: {config_file}[/dim]")
    
    # Check connectivity to Ollama
    console.print(f"[dim]Checking Ollama at {ollama_host}...[/dim]")
    
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            model_count = len(data.get("models", []))
            console.print(f"[green]Connected to Ollama ({model_count} models available)[/green]\n")
            return True
        else:
            raise requests.RequestException(f"Status {response.status_code}")
    except requests.exceptions.ConnectionError:
        console.print(Panel(
            f"[red]Cannot connect to Ollama at:[/red]\n{ollama_host}\n\n"
            "[yellow]Possible solutions:[/yellow]\n"
            "1. Start Ollama locally: [cyan]ollama serve[/cyan]\n"
            "2. Configure a remote endpoint from the menu\n"
            "3. Edit config.yaml with a valid host",
            title="[red]Connection Failed[/red]",
            border_style="red"
        ))
        
        if Confirm.ask("Continue anyway?", default=False):
            return True
        return False
    except requests.exceptions.Timeout:
        console.print(Panel(
            f"[red]Connection timeout to:[/red]\n{ollama_host}\n\n"
            "The server is not responding. Check if the host is correct.",
            title="[red]Timeout[/red]",
            border_style="red"
        ))
        
        if Confirm.ask("Continue anyway?", default=False):
            return True
        return False
    except Exception as e:
        console.print(f"[yellow]Warning: Could not verify Ollama connection: {e}[/yellow]\n")
        return True


def main():
    """CLI entry point."""
    try:
        if not check_ollama_config():
            console.print("[dim]Exiting...[/dim]")
            sys.exit(1)
        main_menu()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
