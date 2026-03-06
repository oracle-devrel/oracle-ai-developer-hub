"""Visualization models and components for reasoning agents."""
from agent_reasoning.visualization.models import (
    TaskStatus,
    TreeNode,
    SubTask,
    VotingSample,
    ReflectionIteration,
    RefinementIteration,
    PipelineIteration,
    ReActStep,
    ChainStep,
    StreamEvent,
)
from agent_reasoning.visualization.base import BaseVisualizer
from agent_reasoning.visualization.tree_viz import TreeVisualizer
from agent_reasoning.visualization.task_viz import TaskVisualizer
from agent_reasoning.visualization.voting_viz import VotingVisualizer
from agent_reasoning.visualization.diff_viz import DiffVisualizer
from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer
from agent_reasoning.visualization.step_viz import StepVisualizer

VISUALIZER_MAP = {
    "tot": TreeVisualizer,
    "tree_of_thoughts": TreeVisualizer,
    "decomposed": TaskVisualizer,
    "least_to_most": TaskVisualizer,
    "ltm": TaskVisualizer,
    # recursive/rlm uses text mode - no structured streaming
    "consistency": VotingVisualizer,
    "self_consistency": VotingVisualizer,
    "reflection": DiffVisualizer,
    "self_reflection": DiffVisualizer,
    "refinement": DiffVisualizer,
    "refinement_loop": DiffVisualizer,
    "iterative_refinement": DiffVisualizer,
    "complex_refinement": None,  # Uses text mode with rich formatting
    "pipeline": None,
    "react": SwimlaneVisualizer,
    "cot": StepVisualizer,
    "chain_of_thought": StepVisualizer,
    "standard": None,
}


def get_visualizer(strategy: str, **kwargs):
    """Get the appropriate visualizer for a strategy."""
    viz_class = VISUALIZER_MAP.get(strategy.lower())
    if viz_class:
        return viz_class(**kwargs)
    return None


__all__ = [
    "TaskStatus",
    "TreeNode",
    "SubTask",
    "VotingSample",
    "ReflectionIteration",
    "RefinementIteration",
    "PipelineIteration",
    "ReActStep",
    "ChainStep",
    "StreamEvent",
    "BaseVisualizer",
    "TreeVisualizer",
    "TaskVisualizer",
    "VotingVisualizer",
    "DiffVisualizer",
    "SwimlaneVisualizer",
    "StepVisualizer",
    "VISUALIZER_MAP",
    "get_visualizer",
]
