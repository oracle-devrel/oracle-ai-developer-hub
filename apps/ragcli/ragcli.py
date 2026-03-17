#!/usr/bin/env python3
"""
ragcli: Premium RAG Command Center for Oracle Database 26ai.
Direct script entry point.
"""
import sys
import os

# Add the current directory to sys.path to ensure ragcli package is found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ragcli.cli.main import app, run_repl

def main():
    """Main entry point logic."""
    if len(sys.argv) == 1:
        # No arguments provided, launch the interactive Gemini-style REPL
        try:
            run_repl()
        except KeyboardInterrupt:
            print("\n\n   [dim white]Session terminated by user.[/dim white]")
            sys.exit(0)
    else:
        # Arguments provided, pass to typer app for sub-command execution
        app()

if __name__ == "__main__":
    main()
