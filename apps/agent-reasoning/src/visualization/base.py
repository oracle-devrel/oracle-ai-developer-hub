# src/visualization/base.py
from abc import ABC, abstractmethod
from typing import Any, Generator
from rich.console import Console, RenderableType
from rich.live import Live

from .models import StreamEvent

class BaseVisualizer(ABC):
    """Base class for all visualizers."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.state = {}

    @abstractmethod
    def render(self) -> RenderableType:
        """Return current Rich renderable for the visualization state."""
        pass

    @abstractmethod
    def update(self, event: StreamEvent) -> None:
        """Update internal state with new event."""
        pass

    def reset(self) -> None:
        """Reset visualizer state."""
        self.state = {}

    def run(self, event_stream: Generator[StreamEvent, None, None]) -> None:
        """Run visualization with live updates."""
        import time
        last_render = 0
        render_interval = 0.15
        with Live(self.render(), console=self.console, refresh_per_second=4, vertical_overflow="visible") as live:
            for event in event_stream:
                self.update(event)
                now = time.time()
                is_structural = event.event_type in ("refinement", "pipeline", "iteration", "phase", "final")
                if is_structural or (now - last_render) >= render_interval:
                    live.update(self.render())
                    last_render = now
            # Final render
            live.update(self.render())
