# src/visualization/pipeline_viz.py
from typing import Dict, List, Optional
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.table import Table

from .base import BaseVisualizer
from .models import StreamEvent, PipelineIteration


# Stage metadata
STAGE_ICONS = ["🔬", "🏗️", "📚", "💡", "✨"]
STAGE_NAMES = [
    "Technical Accuracy",
    "Structure & Clarity",
    "Technical Depth",
    "Examples & Analogies",
    "Professional Polish",
]


class PipelineVisualizer(BaseVisualizer):
    """Visualizer for the Complex Refinement Pipeline - 5-stage optimization."""

    def __init__(self, query: str = "", score_threshold: float = 0.9, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.score_threshold = score_threshold
        # Track state per stage: {stage_index: list of PipelineIteration}
        self.stages: Dict[int, List[PipelineIteration]] = {}
        self.current_stage: Optional[int] = None
        self.current_phase = "init"
        self.streaming_text = ""
        self._dirty = False  # init, generating, critiquing, refining, complete

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "pipeline" and isinstance(event.data, PipelineIteration):
            pi = event.data
            if pi.stage_index not in self.stages:
                self.stages[pi.stage_index] = []
            # Update or append
            existing = [x for x in self.stages[pi.stage_index]
                        if x.iteration_in_stage == pi.iteration_in_stage]
            if existing:
                existing[0].__dict__.update(pi.__dict__)
            else:
                self.stages[pi.stage_index].append(pi)
            self.current_stage = pi.stage_index
            self.streaming_text = ""
            self._dirty = True
        elif event.event_type == "query" and isinstance(event.data, str):
            self.query = event.data
            self._dirty = True
        elif event.event_type == "phase" and isinstance(event.data, str):
            self.current_phase = event.data
            self.streaming_text = ""
            self._dirty = True
        elif event.event_type == "text" and isinstance(event.data, str):
            self.streaming_text += event.data
            self._dirty = True
        elif event.event_type == "final":
            self.streaming_text = ""
            self._dirty = True

    def _make_score_bar(self, score: float, width: int = 15) -> Text:
        """Create a colored score bar."""
        filled = int(score * width)
        empty = width - filled
        bar = Text()
        if score >= 0.9:
            color = "bold green"
        elif score >= 0.7:
            color = "bold yellow"
        else:
            color = "bold red"
        bar.append("█" * filled, style=color)
        bar.append("░" * empty, style="dim")
        bar.append(f" {score:.2f}", style=color)
        return bar

    def _truncate(self, text: str, max_chars: int = 800) -> str:
        """Truncate text to max_chars, appending an ellipsis if needed."""
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def render(self) -> RenderableType:
        self._dirty = False
        elements = []

        # Header
        header = Text()
        header.append("Query: ", style="bold")
        header.append(self.query)

        elements.append(Panel(
            header,
            title="[bold magenta]🔄 Complex Refinement Pipeline[/bold magenta] [dim](5-stage optimization)[/dim]",
            border_style="magenta"
        ))

        # Pipeline progress bar - vertical layout to avoid line-wrap miscalculation
        completed = sum(1 for s in self.stages.values()
                        if s and s[-1].is_stage_complete)
        progress_lines = Text()
        progress_lines.append(f"  Stages: {completed}/5 complete\n", style="bold")

        for i in range(5):
            icon = STAGE_ICONS[i]
            name = STAGE_NAMES[i]

            if i in self.stages:
                iters = self.stages[i]
                last = iters[-1] if iters else None
                if last and last.is_stage_complete:
                    progress_lines.append(f"\n  {icon} {name}", style="bold green")
                    progress_lines.append(f"  [score: {last.score:.2f}]", style="bold green")
                elif last and last.score > 0:
                    progress_lines.append(f"\n  {icon} {name}", style="bold yellow")
                    progress_lines.append(f"  [score: {last.score:.2f}]", style="yellow")
                else:
                    progress_lines.append(f"\n  {icon} {name}", style="bold cyan")
                    progress_lines.append("  ...", style="cyan")
            elif self.current_stage is not None and i == self.current_stage + 1 and self.current_phase == "generating":
                progress_lines.append(f"\n  {icon} {name}", style="bold white")
                progress_lines.append("  next", style="bold white")
            else:
                progress_lines.append(f"\n  {icon} {name}", style="dim")
                progress_lines.append("  pending", style="dim")

        elements.append(Panel(
            progress_lines,
            title="[bold]Pipeline Progress[/bold]",
            border_style="white"
        ))

        # Show details for each stage that has data
        for stage_idx in sorted(self.stages.keys()):
            iters = self.stages[stage_idx]
            if not iters:
                continue

            icon = STAGE_ICONS[stage_idx] if stage_idx < 5 else "🔧"
            name = STAGE_NAMES[stage_idx] if stage_idx < 5 else f"Stage {stage_idx + 1}"
            last_iter = iters[-1]

            stage_elements = []

            # Show iterations for this stage
            for pi in iters:
                iter_parts = []

                # Score
                if pi.score > 0:
                    score_line = Text()
                    score_line.append(f"Iteration {pi.iteration_in_stage}: ", style="bold")
                    iter_parts.append(Group(score_line, self._make_score_bar(pi.score)))

                # Feedback (compact)
                if pi.feedback:
                    feedback_text = self._truncate(pi.feedback, 400)
                    iter_parts.append(Panel(
                        Text.from_markup(feedback_text),
                        title="[dim]Feedback[/dim]",
                        border_style="dim yellow",
                        padding=(0, 1)
                    ))

                if iter_parts:
                    stage_elements.append(Group(*iter_parts))

            # Stage status
            if last_iter.is_stage_complete:
                stage_title = f"{icon} Stage {stage_idx + 1}: {name} ✅ PASSED (score: {last_iter.score:.2f})"
                border = "bold green"
            else:
                stage_title = f"{icon} Stage {stage_idx + 1}: {name} (score: {last_iter.score:.2f})"
                border = "yellow"

            elements.append(Panel(
                Group(*stage_elements) if stage_elements else Text("Evaluating...", style="italic dim"),
                title=f"[bold]{stage_title}[/bold]",
                border_style=border,
                padding=(0, 0)
            ))

        # Live streaming panel for active generation
        if self.streaming_text:
            phase_labels = {
                "draft": "📝 Generating draft...",
                "generating": "📝 Generating...",
                "critique": "🔍 Evaluating...",
                "improvement": "✏️  Refining...",
            }
            label = phase_labels.get(self.current_phase, "⏳ Processing...")
            stream_content = Text()
            stream_content.append(f"{label}\n", style="bold yellow")
            preview = self.streaming_text[-500:] if len(self.streaming_text) > 500 else self.streaming_text
            if len(self.streaming_text) > 500:
                preview = "..." + preview
            stream_content.append(preview, style="dim")
            elements.append(Panel(
                stream_content,
                title="[bold yellow]Streaming[/bold yellow]",
                border_style="yellow",
                padding=(0, 1)
            ))

        # Final summary if pipeline is complete
        if self.stages:
            all_complete = all(
                s and s[-1].is_stage_complete
                for s in self.stages.values()
            ) and len(self.stages) == 5

            if all_complete:
                summary = Text()
                summary.append("✅ All 5 stages passed!\n\n", style="bold green")
                for i in range(5):
                    iters = self.stages.get(i, [])
                    if iters:
                        last = iters[-1]
                        summary.append(f"  {STAGE_ICONS[i]} {STAGE_NAMES[i]}: ", style="bold")
                        score_color = "green" if last.score >= 0.9 else "yellow"
                        summary.append(f"{last.score:.2f}", style=f"bold {score_color}")
                        summary.append(f" ({len(iters)} iteration{'s' if len(iters) > 1 else ''})\n")

                elements.append(Panel(
                    summary,
                    title="[bold]📊 Pipeline Summary[/bold]",
                    border_style="bold green"
                ))

        # Show waiting state if no stages yet
        if not self.stages and not self.streaming_text:
            waiting = Text()
            waiting.append("⏳ ", style="bold yellow")
            waiting.append("Generating initial draft...", style="italic yellow")
            elements.append(Panel(waiting, border_style="yellow"))

        return Group(*elements)
