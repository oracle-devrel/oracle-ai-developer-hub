import os
from pathlib import Path
import questionary
from typing import Optional, List
from questionary import Choice

def interactive_file_selector(start_path: Path = Path(".")) -> Optional[Path]:
    """
    Interactively navigate directories and select a file.
    """
    current_path = start_path.resolve()

    while True:
        # Get list of files and directories
        try:
            items = sorted(list(current_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            print(f"Permission denied: {current_path}")
            current_path = current_path.parent
            continue

        choices = []
        
        # Add parent directory option if not at root
        if current_path.parent != current_path:
            choices.append(Choice(title=".. (Go Up)", value=current_path.parent))

        # Add directories and files
        for item in items:
            if item.name.startswith('.'):
                continue
                
            if item.is_dir():
                title = f"📁 {item.name}/"
                choices.append(Choice(title=title, value=item))
            else:
                title = f"📄 {item.name}"
                choices.append(Choice(title=title, value=item))

        CANCEL_SENTINEL = object()
        choices.append(Choice(title="❌ Cancel", value=CANCEL_SENTINEL))

        selection = questionary.select(
            f"Current Directory: {current_path}",
            choices=choices,
            style=questionary.Style([
                ('qmark', 'fg:#5f819d bold'),
                ('question', 'fg:#282828 bold'),
                ('answer', 'fg:#5f819d bold'),
                ('pointer', 'fg:#ff0055 bold'), 
                ('highlighted', 'fg:#ff0055 bold'), 
                ('selected', 'fg:#cc5454'),
                ('separator', 'fg:#cc5454'),
                ('instruction', 'fg:#666666 italic')
            ])
        ).ask()

        if selection is CANCEL_SENTINEL or selection is None:
            return None
        
        if selection == current_path.parent:
            current_path = selection
        elif selection.is_dir():
            current_path = selection
        else:
            return selection
