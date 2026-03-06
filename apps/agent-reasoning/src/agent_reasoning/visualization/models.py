# src/visualization/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TreeNode:
    """Tree of Thoughts node."""
    id: str
    depth: int
    content: str
    score: Optional[float] = None
    parent_id: Optional[str] = None
    is_best: bool = False
    is_pruned: bool = False

@dataclass
class SubTask:
    """Decomposed/Least-to-Most/Recursive task."""
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    progress: float = 0.0
    parent_id: Optional[int] = None

@dataclass
class VotingSample:
    """Self-Consistency voting sample."""
    id: int
    answer: str = ""
    reasoning: str = ""
    votes: int = 0
    is_winner: bool = False
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class ReflectionIteration:
    """Self-Reflection iteration."""
    iteration: int
    draft: str = ""
    critique: Optional[str] = None
    improvement: Optional[str] = None
    is_correct: bool = False


@dataclass
class RefinementIteration:
    """Refinement Loop iteration with score-based feedback."""
    iteration: int
    draft: str = ""
    critique: Optional[str] = None
    feedback: Optional[str] = None
    score: float = 0.0
    is_accepted: bool = False


@dataclass
class PipelineIteration:
    """Complex Refinement Pipeline iteration tracking."""
    stage_index: int
    stage_name: str
    iteration_in_stage: int
    draft: str = ""
    critique: Optional[str] = None
    feedback: Optional[str] = None
    score: float = 0.0
    is_stage_complete: bool = False
    is_pipeline_complete: bool = False


@dataclass
class ReActStep:
    """ReAct reasoning step."""
    step: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class ChainStep:
    """Chain-of-Thought step."""
    step: int
    content: str = ""
    total_steps: Optional[int] = None
    is_final: bool = False
    icon: str = "🔢"

@dataclass
class StreamEvent:
    """Wrapper for streaming events."""
    event_type: str  # "node", "task", "sample", "iteration", "refinement", "pipeline", "react_step", "chain_step", "text", "final"
    data: Union[TreeNode, SubTask, VotingSample, ReflectionIteration, RefinementIteration, PipelineIteration, ReActStep, ChainStep, str]
    is_update: bool = False  # True if updating existing item
