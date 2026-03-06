# src/visualization/diff_viz.py
import difflib
from typing import Dict, List, Union
from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.columns import Columns
from rich.table import Table

from .base import BaseVisualizer
from .models import StreamEvent, ReflectionIteration, RefinementIteration


class DiffVisualizer(BaseVisualizer):
    """Visualizer for Self-Reflection and Refinement Loop - iterations with diff highlighting."""

    def __init__(self, query: str = "", max_iterations: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.max_iterations = max_iterations
        self.iterations: Dict[int, Union[ReflectionIteration, RefinementIteration]] = {}
        self.current_phase = "draft"  # draft, critique, improvement
        self.mode = "reflection"  # reflection or refinement
        self.streaming_text = ""  # Live text accumulator for current phase
        self._dirty = False  # True when state changed since last render  # reflection or refinement

    def update(self, event: StreamEvent) -> None:
        if event.event_type == "iteration" and isinstance(event.data, ReflectionIteration):
            iteration = event.data
            self.iterations[iteration.iteration] = iteration
            self.mode = "reflection"
            self.streaming_text = ""
            self._dirty = True
        elif event.event_type == "refinement" and isinstance(event.data, RefinementIteration):
            iteration = event.data
            # For update events, merge improvement into existing iteration
            if event.is_update and iteration.iteration in self.iterations:
                existing = self.iterations[iteration.iteration]
                if isinstance(existing, RefinementIteration) and iteration.improvement:
                    existing.improvement = iteration.improvement
            else:
                self.iterations[iteration.iteration] = iteration
            self.mode = "refinement"
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

    def _compute_diff(self, old_text: str, new_text: str) -> Text:
        """Compute word-level diff with highlighting."""
        result = Text()

        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.append(" ".join(old_words[i1:i2]) + " ")
            elif tag == 'replace':
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == 'insert':
                result.append(" ".join(new_words[j1:j2]) + " ", style="bold green on dark_green")
            elif tag == 'delete':
                pass  # Don't show deleted in final version

        return result

    def _make_score_bar(self, score: float, width: int = 20) -> Text:
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

    def _make_iteration_progress(self) -> Text:
        """Create a visual progress indicator."""
        result = Text()
        for i in range(1, self.max_iterations + 1):
            if i in self.iterations:
                it = self.iterations[i]
                if self._is_iteration_complete(it):
                    result.append("●", style="bold green")
                elif isinstance(it, RefinementIteration) and it.score > 0:
                    result.append("●", style="bold yellow")
                else:
                    result.append("●", style="bold cyan")
            elif i == len(self.iterations) + 1:
                result.append("◐", style="bold white")  # current
            else:
                result.append("○", style="dim")
            if i < self.max_iterations:
                result.append("───", style="dim")
        result.append(f"  {len(self.iterations)}/{self.max_iterations}", style="bold")
        return result

    def _is_iteration_complete(self, iteration) -> bool:
        """Check if an iteration is complete (accepted or correct)."""
        if isinstance(iteration, RefinementIteration):
            return iteration.is_accepted
        elif isinstance(iteration, ReflectionIteration):
            return iteration.is_correct
        return False

    def _truncate(self, text: str, max_chars: int = 800) -> str:
        """Truncate text to max_chars, appending an ellipsis if needed."""
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def render(self) -> RenderableType:
        self._dirty = False
        elements = []

        # Header with progress
        if self.mode == "refinement":
            title = "[bold cyan]🔄 Refinement Loop[/bold cyan] [dim](score-based iterative improvement)[/dim]"
        else:
            title = f"[bold cyan]🔄 Self-Reflection[/bold cyan] [dim](max {self.max_iterations} iterations)[/dim]"

        header_content = Text()
        header_content.append("Query: ", style="bold")
        header_content.append(self._truncate(self.query, 200))
        header_content.append("\n")
        header_content.append("Progress: ", style="bold")

        elements.append(Panel(
            Group(header_content, self._make_iteration_progress()),
            title=title,
            border_style="cyan"
        ))

        if not self.iterations:
            # No iterations yet — show streaming text from draft phase
            phase_text = Text()
            if self.current_phase == "draft":
                phase_text.append("⏳ ", style="bold yellow")
                phase_text.append("Generating initial draft...\n", style="italic yellow")
            else:
                phase_text.append("⏳ ", style="bold yellow")
                phase_text.append("Starting...\n", style="italic")
            if self.streaming_text:
                preview = self.streaming_text[-500:] if len(self.streaming_text) > 500 else self.streaming_text
                if len(self.streaming_text) > 500:
                    preview = "..." + preview
                phase_text.append(preview, style="dim")
            elements.append(Panel(phase_text, border_style="yellow"))
            return Group(*elements)

        # Render each iteration
        sorted_keys = sorted(self.iterations.keys())
        last_key = sorted_keys[-1]

        for idx, i in enumerate(sorted_keys):
            iteration = self.iterations[i]
            is_complete = self._is_iteration_complete(iteration)
            is_latest = (i == last_key)

            # Build iteration title
            iter_title = f"Iteration {i}"
            if isinstance(iteration, RefinementIteration):
                if iteration.is_accepted:
                    iter_title += f" ✅ ACCEPTED (score: {iteration.score:.2f})"
                elif iteration.score > 0:
                    iter_title += f" (score: {iteration.score:.2f})"
            elif isinstance(iteration, ReflectionIteration) and iteration.is_correct:
                iter_title += " ✅ CORRECT"

            border = "bold green" if is_complete else ("white" if iteration.critique else "cyan")

            # Collapsed view for older completed iterations — just score bar + brief summary
            if not is_latest and iteration.critique:
                collapsed = Text()
                if isinstance(iteration, RefinementIteration) and iteration.score > 0:
                    collapsed.append("Score: ", style="bold")
                    score_bar = self._make_score_bar(iteration.score)
                    feedback_preview = ""
                    if isinstance(iteration, RefinementIteration) and iteration.feedback:
                        feedback_preview = self._truncate(iteration.feedback, 120)
                    elif iteration.critique:
                        feedback_preview = self._truncate(iteration.critique, 120)
                    elements.append(Panel(
                        Group(collapsed, score_bar, Text(feedback_preview, style="dim")),
                        title=f"[bold]{iter_title}[/bold]",
                        border_style=border,
                        padding=(0, 1)
                    ))
                else:
                    critique_preview = self._truncate(iteration.critique, 150)
                    collapsed.append(critique_preview, style="dim")
                    elements.append(Panel(
                        collapsed,
                        title=f"[bold]{iter_title}[/bold]",
                        border_style=border,
                        padding=(0, 1)
                    ))
                continue

            # Full view for latest / active iteration
            iter_elements = []

            # Draft panel
            if iteration.draft:
                draft_text = self._truncate(iteration.draft)
                iter_elements.append(Panel(
                    draft_text,
                    title="[bold blue]📝 Draft[/bold blue]",
                    border_style="blue",
                    padding=(0, 1)
                ))

            # Critique/Feedback panel
            if iteration.critique:
                critique_parts = []

                # Score bar for refinement
                if isinstance(iteration, RefinementIteration) and iteration.score > 0:
                    score_text = Text()
                    score_text.append("Score: ", style="bold")
                    critique_parts.append(Group(
                        score_text,
                        self._make_score_bar(iteration.score),
                        Text()  # spacer
                    ))

                # Feedback text (prefer extracted feedback over raw critique)
                if isinstance(iteration, RefinementIteration) and iteration.feedback:
                    feedback_display = self._truncate(iteration.feedback, 600)
                else:
                    feedback_display = self._truncate(iteration.critique, 600)

                critique_parts.append(Text.from_markup(feedback_display))

                critique_title = "[bold]🔍 Critique[/bold]"

                iter_elements.append(Panel(
                    Group(*critique_parts),
                    title=critique_title,
                    border_style="yellow",
                    padding=(0, 1)
                ))

            # Improvement with diff highlighting
            if isinstance(iteration, ReflectionIteration) and iteration.improvement:
                if idx > 0:
                    prev_key = sorted_keys[idx - 1]
                    prev = self.iterations[prev_key]
                    prev_text = prev.improvement or prev.draft if isinstance(prev, ReflectionIteration) else prev.draft
                    diff_text = self._compute_diff(prev_text, iteration.improvement)
                else:
                    diff_text = self._compute_diff(iteration.draft, iteration.improvement)

                iter_elements.append(Panel(
                    diff_text,
                    title="[bold]✏️  Refined[/bold]",
                    border_style="green",
                    padding=(0, 1)
                ))
            elif isinstance(iteration, RefinementIteration) and iteration.improvement:
                diff_text = self._compute_diff(iteration.draft, iteration.improvement)
                iter_elements.append(Panel(
                    diff_text,
                    title="[bold]✏️  Refined Version[/bold] [dim](changes highlighted)[/dim]",
                    border_style="green",
                    padding=(0, 1)
                ))

            elements.append(Panel(
                Group(*iter_elements) if iter_elements else Text("Processing...", style="italic dim"),
                title=f"[bold]{iter_title}[/bold]",
                border_style=border,
                padding=(0, 0)
            ))

        # Live streaming panel — show current generation in progress
        if self.streaming_text:
            phase_labels = {
                "draft": "📝 Generating draft...",
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

        # Summary panel
        last_iter = self.iterations.get(max(self.iterations.keys())) if self.iterations else None
        if last_iter and self._is_iteration_complete(last_iter):
            summary_parts = []
            if isinstance(last_iter, RefinementIteration):
                summary_parts.append(Text.from_markup(
                    f"[bold green]✅ Quality threshold met![/bold green]\n"
                    f"Final Score: [bold]{last_iter.score:.2f}[/bold]  |  "
                    f"Iterations: [bold]{len(self.iterations)}[/bold]/{self.max_iterations}"
                ))
            else:
                summary_parts.append(Text.from_markup(
                    f"[bold green]✅ Converged![/bold green]\n"
                    f"Iterations: [bold]{len(self.iterations)}[/bold]/{self.max_iterations}"
                ))
            elements.append(Panel(
                Group(*summary_parts),
                title="[bold]📊 Summary[/bold]",
                border_style="bold green"
            ))

        return Group(*elements)
