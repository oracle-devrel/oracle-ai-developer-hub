# Agent-Reasoning Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate agent-reasoning library into agentic_rag with ensemble voting, unified chat UI, A2A support, and database logging.

**Architecture:** Two-package approach - agent-reasoning published to PyPI as standalone library, agentic_rag imports via pip and adds RAG/A2A/logging wrappers. Ensemble runs strategies in parallel with majority voting via semantic similarity clustering.

**Tech Stack:** Python 3.10+, Ollama, FastAPI, Gradio, Oracle DB 26ai, sentence-transformers (embeddings), asyncio (parallel execution)

---

## Phase 1: Prepare agent-reasoning for PyPI

### Task 1.1: Restructure agent-reasoning for PyPI packaging

**Files:**
- Create: `/home/ubuntu/git/agent-reasoning/pyproject.toml`
- Create: `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/__init__.py`
- Move: `/home/ubuntu/git/agent-reasoning/src/agents/` → `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/agents/`
- Move: `/home/ubuntu/git/agent-reasoning/src/client.py` → `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/client.py`
- Move: `/home/ubuntu/git/agent-reasoning/src/interceptor.py` → `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/interceptor.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-reasoning"
version = "1.0.0"
description = "Transform LLMs into robust problem-solving agents with advanced reasoning strategies"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["llm", "reasoning", "agents", "cot", "tot", "react"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28.0",
    "termcolor>=2.0.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
server = ["fastapi>=0.100.0", "uvicorn>=0.23.0"]
dev = ["pytest>=7.0.0", "pytest-asyncio>=0.21.0"]

[project.urls]
Homepage = "https://github.com/your-username/agent-reasoning"
Repository = "https://github.com/your-username/agent-reasoning"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: Create directory structure**

Run:
```bash
cd /home/ubuntu/git/agent-reasoning
mkdir -p src/agent_reasoning/agents
mkdir -p src/agent_reasoning/visualization
```

**Step 3: Move files to new structure**

Run:
```bash
cd /home/ubuntu/git/agent-reasoning
# Copy agents
cp src/agents/*.py src/agent_reasoning/agents/
# Copy core files
cp src/client.py src/agent_reasoning/
cp src/interceptor.py src/agent_reasoning/
# Copy visualization if exists
cp -r src/visualization/*.py src/agent_reasoning/visualization/ 2>/dev/null || true
```

**Step 4: Create src/agent_reasoning/__init__.py**

```python
"""
Agent Reasoning: Transform LLMs into robust problem-solving agents.

Usage:
    from agent_reasoning import ReasoningInterceptor
    from agent_reasoning.agents import CoTAgent, ToTAgent
    from agent_reasoning.ensemble import ReasoningEnsemble
"""

from agent_reasoning.interceptor import ReasoningInterceptor, AGENT_MAP
from agent_reasoning.client import OllamaClient

__version__ = "1.0.0"
__all__ = ["ReasoningInterceptor", "OllamaClient", "AGENT_MAP"]
```

**Step 5: Create src/agent_reasoning/agents/__init__.py**

```python
"""
Reasoning strategy agents.

Available agents:
- StandardAgent: Direct LLM generation (baseline)
- CoTAgent: Chain-of-Thought reasoning
- ToTAgent: Tree of Thoughts exploration
- ReActAgent: Reason + Act with tools
- SelfReflectionAgent: Draft → Critique → Refine
- ConsistencyAgent: Self-consistency voting
- DecomposedAgent: Problem decomposition
- LeastToMostAgent: Least-to-most reasoning
- RecursiveAgent: Recursive processing
"""

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.agents.standard import StandardAgent
from agent_reasoning.agents.cot import CoTAgent
from agent_reasoning.agents.tot import ToTAgent
from agent_reasoning.agents.react import ReActAgent
from agent_reasoning.agents.self_reflection import SelfReflectionAgent
from agent_reasoning.agents.consistency import ConsistencyAgent
from agent_reasoning.agents.decomposed import DecomposedAgent
from agent_reasoning.agents.least_to_most import LeastToMostAgent
from agent_reasoning.agents.recursive import RecursiveAgent

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "chain_of_thought": CoTAgent,
    "tot": ToTAgent,
    "tree_of_thoughts": ToTAgent,
    "react": ReActAgent,
    "self_reflection": SelfReflectionAgent,
    "reflection": SelfReflectionAgent,
    "consistency": ConsistencyAgent,
    "self_consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
    "ltm": LeastToMostAgent,
    "recursive": RecursiveAgent,
    "rlm": RecursiveAgent,
}

__all__ = [
    "BaseAgent",
    "StandardAgent",
    "CoTAgent",
    "ToTAgent",
    "ReActAgent",
    "SelfReflectionAgent",
    "ConsistencyAgent",
    "DecomposedAgent",
    "LeastToMostAgent",
    "RecursiveAgent",
    "AGENT_MAP",
]
```

**Step 6: Update imports in all agent files**

For each file in `src/agent_reasoning/agents/`, update imports from:
```python
from src.agents.base import BaseAgent
from src.client import OllamaClient
```
to:
```python
from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.client import OllamaClient
```

Run:
```bash
cd /home/ubuntu/git/agent-reasoning/src/agent_reasoning
# Fix base.py
sed -i 's/from src.client/from agent_reasoning.client/g' agents/base.py
# Fix all agent files
for f in agents/*.py; do
    sed -i 's/from src.agents.base/from agent_reasoning.agents.base/g' "$f"
    sed -i 's/from src.visualization/from agent_reasoning.visualization/g' "$f"
done
# Fix interceptor.py
sed -i 's/from src.agents./from agent_reasoning.agents./g' interceptor.py
```

**Step 7: Verify package structure**

Run:
```bash
cd /home/ubuntu/git/agent-reasoning
find src/agent_reasoning -name "*.py" | head -20
```

Expected output:
```
src/agent_reasoning/__init__.py
src/agent_reasoning/client.py
src/agent_reasoning/interceptor.py
src/agent_reasoning/agents/__init__.py
src/agent_reasoning/agents/base.py
src/agent_reasoning/agents/cot.py
...
```

**Step 8: Commit**

```bash
cd /home/ubuntu/git/agent-reasoning
git add .
git commit -m "refactor: restructure for PyPI packaging

- Move src/ to src/agent_reasoning/
- Add pyproject.toml for modern packaging
- Update all internal imports
- Add package __init__.py with public API"
```

---

### Task 1.2: Add ReasoningEnsemble class

**Files:**
- Create: `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/ensemble.py`
- Modify: `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/__init__.py`

**Step 1: Create ensemble.py**

```python
"""
ReasoningEnsemble: Run multiple reasoning strategies in parallel with majority voting.

Usage:
    from agent_reasoning.ensemble import ReasoningEnsemble

    ensemble = ReasoningEnsemble(model_name="gemma3:270m")
    result = await ensemble.run(
        query="What is 2+2?",
        strategies=["cot", "tot", "consistency"]
    )
    print(result["winner"]["response"])
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from agent_reasoning.agents import AGENT_MAP


class ReasoningEnsemble:
    """
    Orchestrates multiple reasoning strategies in parallel and aggregates
    results via majority voting using semantic similarity clustering.
    """

    def __init__(
        self,
        model_name: str = "gemma3:270m",
        similarity_threshold: float = 0.85,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the ensemble.

        Args:
            model_name: Base LLM model to use for all strategies
            similarity_threshold: Cosine similarity threshold for clustering (0.0-1.0)
            embedding_model: Sentence transformer model for response embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.embedding_model_name = embedding_model
        self._embedding_model = None
        self._executor = ThreadPoolExecutor(max_workers=10)

    @property
    def embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers required for ensemble voting. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedding_model

    @property
    def available_strategies(self) -> List[str]:
        """Return list of available strategy names."""
        return list(set(AGENT_MAP.keys()))

    async def run(
        self,
        query: str,
        strategies: List[str],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run ensemble of reasoning strategies.

        Args:
            query: The question/prompt to process
            strategies: List of strategy names to run (e.g., ["cot", "tot"])
            config: Optional per-strategy configuration
                   e.g., {"tot": {"depth": 3}, "consistency": {"samples": 5}}

        Returns:
            Dict with keys:
                - winner: {strategy, response, vote_count}
                - all_responses: [{strategy, response, duration_ms}, ...]
                - total_duration_ms: float
                - voting_details: {clusters, threshold}
        """
        config = config or {}
        start_time = time.time()

        # Validate strategies
        valid_strategies = []
        for s in strategies:
            if s in AGENT_MAP:
                valid_strategies.append(s)
            else:
                print(f"Warning: Unknown strategy '{s}', skipping")

        if not valid_strategies:
            return {
                "winner": {"strategy": None, "response": "No valid strategies provided", "vote_count": 0},
                "all_responses": [],
                "total_duration_ms": 0,
                "voting_details": None
            }

        # Single strategy - return directly without voting
        if len(valid_strategies) == 1:
            strategy = valid_strategies[0]
            strategy_config = config.get(strategy, {})
            response, duration = await self._run_single_strategy(query, strategy, strategy_config)

            return {
                "winner": {
                    "strategy": strategy,
                    "response": response,
                    "vote_count": 1
                },
                "all_responses": [{
                    "strategy": strategy,
                    "response": response,
                    "duration_ms": duration
                }],
                "total_duration_ms": (time.time() - start_time) * 1000,
                "voting_details": None  # No voting for single strategy
            }

        # Multiple strategies - run in parallel
        responses = await self._run_parallel(query, valid_strategies, config)

        # Perform majority voting
        winner, voting_details = self._majority_vote(responses)

        total_duration = (time.time() - start_time) * 1000

        return {
            "winner": winner,
            "all_responses": responses,
            "total_duration_ms": total_duration,
            "voting_details": voting_details
        }

    async def _run_single_strategy(
        self,
        query: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> tuple[str, float]:
        """Run a single strategy and return (response, duration_ms)."""
        start = time.time()

        # Get agent class and instantiate with config
        agent_class = AGENT_MAP[strategy]

        # Pass config params to agent constructor if supported
        try:
            agent = agent_class(model=self.model_name, **config)
        except TypeError:
            # Agent doesn't accept extra kwargs
            agent = agent_class(model=self.model_name)

        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self._executor,
            agent.run,
            query
        )

        duration = (time.time() - start) * 1000
        return response, duration

    async def _run_parallel(
        self,
        query: str,
        strategies: List[str],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run multiple strategies in parallel."""
        tasks = []
        for strategy in strategies:
            strategy_config = config.get(strategy, {})
            task = self._run_single_strategy(query, strategy, strategy_config)
            tasks.append((strategy, task))

        responses = []
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        for (strategy, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                responses.append({
                    "strategy": strategy,
                    "response": f"Error: {str(result)}",
                    "duration_ms": 0,
                    "error": True
                })
            else:
                response, duration = result
                responses.append({
                    "strategy": strategy,
                    "response": response,
                    "duration_ms": duration,
                    "error": False
                })

        return responses

    def _majority_vote(self, responses: List[Dict[str, Any]]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Cluster responses by semantic similarity and return the most common answer.

        Returns:
            (winner_dict, voting_details_dict)
        """
        # Filter out error responses
        valid_responses = [r for r in responses if not r.get("error", False)]

        if not valid_responses:
            return {
                "strategy": None,
                "response": "All strategies failed",
                "vote_count": 0
            }, {"clusters": [], "threshold": self.similarity_threshold}

        if len(valid_responses) == 1:
            r = valid_responses[0]
            return {
                "strategy": r["strategy"],
                "response": r["response"],
                "vote_count": 1
            }, {"clusters": [[0]], "threshold": self.similarity_threshold}

        # Get embeddings for all responses
        texts = [r["response"] for r in valid_responses]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Cluster by cosine similarity
        clusters = self._cluster_by_similarity(embeddings)

        # Find largest cluster
        largest_cluster = max(clusters, key=len)
        winner_idx = largest_cluster[0]

        # Handle ties - prefer CoT as fallback
        if len([c for c in clusters if len(c) == len(largest_cluster)]) > 1:
            # Multiple clusters of same size - prefer CoT
            for cluster in clusters:
                if len(cluster) == len(largest_cluster):
                    for idx in cluster:
                        if valid_responses[idx]["strategy"] in ["cot", "chain_of_thought"]:
                            winner_idx = idx
                            largest_cluster = cluster
                            break

        winner = valid_responses[winner_idx]

        return {
            "strategy": winner["strategy"],
            "response": winner["response"],
            "vote_count": len(largest_cluster)
        }, {
            "clusters": clusters,
            "threshold": self.similarity_threshold,
            "total_responses": len(valid_responses)
        }

    def _cluster_by_similarity(self, embeddings: np.ndarray) -> List[List[int]]:
        """
        Cluster embeddings by cosine similarity.

        Returns list of clusters, where each cluster is a list of indices.
        """
        n = len(embeddings)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)

        # Compute similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)

        # Greedy clustering
        assigned = [False] * n
        clusters = []

        for i in range(n):
            if assigned[i]:
                continue

            # Start new cluster with this response
            cluster = [i]
            assigned[i] = True

            # Find all similar responses
            for j in range(i + 1, n):
                if not assigned[j] and similarity_matrix[i, j] >= self.similarity_threshold:
                    cluster.append(j)
                    assigned[j] = True

            clusters.append(cluster)

        return clusters

    def run_sync(
        self,
        query: str,
        strategies: List[str],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(query, strategies, config))
```

**Step 2: Update __init__.py to export ReasoningEnsemble**

Add to `/home/ubuntu/git/agent-reasoning/src/agent_reasoning/__init__.py`:

```python
"""
Agent Reasoning: Transform LLMs into robust problem-solving agents.

Usage:
    from agent_reasoning import ReasoningInterceptor, ReasoningEnsemble
    from agent_reasoning.agents import CoTAgent, ToTAgent
"""

from agent_reasoning.interceptor import ReasoningInterceptor, AGENT_MAP
from agent_reasoning.client import OllamaClient
from agent_reasoning.ensemble import ReasoningEnsemble

__version__ = "1.0.0"
__all__ = ["ReasoningInterceptor", "ReasoningEnsemble", "OllamaClient", "AGENT_MAP"]
```

**Step 3: Commit**

```bash
cd /home/ubuntu/git/agent-reasoning
git add src/agent_reasoning/ensemble.py src/agent_reasoning/__init__.py
git commit -m "feat: add ReasoningEnsemble for parallel strategy execution with voting

- Run multiple strategies in parallel via asyncio
- Majority voting using semantic similarity clustering
- Single strategy bypasses voting for efficiency
- Configurable similarity threshold and embedding model"
```

---

### Task 1.3: Test and build PyPI package

**Files:**
- Create: `/home/ubuntu/git/agent-reasoning/tests/test_ensemble.py`

**Step 1: Create test file**

```python
"""Tests for ReasoningEnsemble."""
import pytest
import asyncio
from unittest.mock import Mock, patch
import numpy as np

from agent_reasoning.ensemble import ReasoningEnsemble


class TestReasoningEnsemble:
    """Test suite for ReasoningEnsemble."""

    def test_available_strategies(self):
        """Test that all strategies are available."""
        ensemble = ReasoningEnsemble()
        strategies = ensemble.available_strategies

        assert "cot" in strategies
        assert "tot" in strategies
        assert "react" in strategies
        assert "consistency" in strategies
        assert "standard" in strategies

    def test_single_strategy_no_voting(self):
        """Test that single strategy bypasses voting."""
        ensemble = ReasoningEnsemble()

        with patch.object(ensemble, '_run_single_strategy') as mock_run:
            mock_run.return_value = ("Test response", 100.0)

            result = asyncio.run(ensemble.run("test query", ["cot"]))

            assert result["winner"]["strategy"] == "cot"
            assert result["winner"]["response"] == "Test response"
            assert result["voting_details"] is None

    def test_cluster_by_similarity(self):
        """Test similarity clustering."""
        ensemble = ReasoningEnsemble(similarity_threshold=0.9)

        # Create mock embeddings - two similar, one different
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # Response 0
            [0.99, 0.1, 0.0],  # Response 1 - similar to 0
            [0.0, 1.0, 0.0],  # Response 2 - different
        ])

        clusters = ensemble._cluster_by_similarity(embeddings)

        # Should have 2 clusters
        assert len(clusters) == 2
        # First cluster should have responses 0 and 1
        assert sorted(clusters[0]) == [0, 1] or sorted(clusters[1]) == [0, 1]

    def test_invalid_strategy_skipped(self):
        """Test that invalid strategies are skipped with warning."""
        ensemble = ReasoningEnsemble()

        with patch.object(ensemble, '_run_single_strategy') as mock_run:
            mock_run.return_value = ("Test response", 100.0)

            result = asyncio.run(ensemble.run("test", ["cot", "invalid_strategy"]))

            # Should only run cot
            assert mock_run.call_count == 1

    def test_empty_strategies_returns_error(self):
        """Test handling of empty strategy list."""
        ensemble = ReasoningEnsemble()

        result = asyncio.run(ensemble.run("test", []))

        assert result["winner"]["strategy"] is None
        assert "No valid strategies" in result["winner"]["response"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

Run:
```bash
cd /home/ubuntu/git/agent-reasoning
pip install -e ".[dev]"
pytest tests/test_ensemble.py -v
```

Expected: All tests PASS

**Step 3: Build package**

Run:
```bash
cd /home/ubuntu/git/agent-reasoning
pip install build
python -m build
```

Expected: Creates `dist/agent_reasoning-1.0.0.tar.gz` and `dist/agent_reasoning-1.0.0-py3-none-any.whl`

**Step 4: Install locally to verify**

Run:
```bash
pip install dist/agent_reasoning-1.0.0-py3-none-any.whl
python -c "from agent_reasoning import ReasoningEnsemble; print('Success!')"
```

Expected: Prints "Success!"

**Step 5: Commit**

```bash
cd /home/ubuntu/git/agent-reasoning
git add tests/test_ensemble.py
git commit -m "test: add ensemble unit tests"
```

---

## Phase 2: Create RAGReasoningEnsemble in agentic_rag

### Task 2.1: Add agent-reasoning dependency

**Files:**
- Modify: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/requirements.txt`

**Step 1: Add dependency**

Add to end of requirements.txt:
```
# Local install of agent-reasoning (replace with PyPI version when published)
-e /home/ubuntu/git/agent-reasoning
```

Or if published to PyPI:
```
agent-reasoning>=1.0.0
```

**Step 2: Install**

Run:
```bash
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag
pip install -r requirements.txt
```

**Step 3: Verify import**

Run:
```bash
python -c "from agent_reasoning import ReasoningEnsemble; print('agent-reasoning installed successfully')"
```

**Step 4: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/requirements.txt
git commit -m "deps: add agent-reasoning dependency"
```

---

### Task 2.2: Create RAGReasoningEnsemble wrapper

**Files:**
- Create: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/reasoning/__init__.py`
- Create: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/reasoning/rag_ensemble.py`

**Step 1: Create package directory**

Run:
```bash
mkdir -p /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/reasoning
```

**Step 2: Create __init__.py**

```python
"""
Reasoning module for agentic_rag.

Wraps agent_reasoning library with RAG context, A2A protocol, and database logging.
"""

from .rag_ensemble import RAGReasoningEnsemble

__all__ = ["RAGReasoningEnsemble"]
```

**Step 3: Create rag_ensemble.py**

```python
"""
RAGReasoningEnsemble: Extends agent_reasoning.ReasoningEnsemble with RAG integration.

Adds:
- RAG context retrieval before reasoning
- Database logging of reasoning events
- Streaming execution trace for UI
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

from agent_reasoning import ReasoningEnsemble
from agent_reasoning.agents import AGENT_MAP


@dataclass
class ExecutionEvent:
    """Represents a single event in the execution trace."""
    timestamp: str
    event_type: str  # "start", "rag", "strategy_start", "strategy_complete", "voting", "complete"
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class ReasoningResult:
    """Complete result of reasoning ensemble execution."""
    winner: Dict[str, Any]
    all_responses: List[Dict[str, Any]]
    execution_trace: List[ExecutionEvent] = field(default_factory=list)
    rag_context: Optional[Dict[str, Any]] = None
    total_duration_ms: float = 0
    voting_details: Optional[Dict[str, Any]] = None


class RAGReasoningEnsemble:
    """
    Extends ReasoningEnsemble with RAG context retrieval and database logging.

    Usage:
        ensemble = RAGReasoningEnsemble(
            model_name="gemma3:270m",
            vector_store=my_vector_store,
            event_logger=my_event_logger
        )

        result = await ensemble.run(
            query="What is machine learning?",
            strategies=["cot", "tot"],
            use_rag=True,
            collection="PDF"
        )
    """

    STRATEGY_ICONS = {
        "standard": "📝",
        "cot": "🔗",
        "chain_of_thought": "🔗",
        "tot": "🌳",
        "tree_of_thoughts": "🌳",
        "react": "🛠️",
        "self_reflection": "🪞",
        "reflection": "🪞",
        "consistency": "🔄",
        "self_consistency": "🔄",
        "decomposed": "🧩",
        "least_to_most": "📈",
        "ltm": "📈",
        "recursive": "🔁",
        "rlm": "🔁",
    }

    STRATEGY_NAMES = {
        "standard": "Standard",
        "cot": "Chain-of-Thought",
        "chain_of_thought": "Chain-of-Thought",
        "tot": "Tree of Thoughts",
        "tree_of_thoughts": "Tree of Thoughts",
        "react": "ReAct",
        "self_reflection": "Self-Reflection",
        "reflection": "Self-Reflection",
        "consistency": "Self-Consistency",
        "self_consistency": "Self-Consistency",
        "decomposed": "Decomposed",
        "least_to_most": "Least-to-Most",
        "ltm": "Least-to-Most",
        "recursive": "Recursive",
        "rlm": "Recursive",
    }

    def __init__(
        self,
        model_name: str = "gemma3:270m",
        vector_store=None,
        event_logger=None,
        similarity_threshold: float = 0.85
    ):
        """
        Initialize RAGReasoningEnsemble.

        Args:
            model_name: Base LLM model for reasoning
            vector_store: Vector store for RAG retrieval (OraDBVectorStore or VectorStore)
            event_logger: OraDBEventLogger for logging reasoning events
            similarity_threshold: Threshold for majority voting clustering
        """
        self.model_name = model_name
        self.vector_store = vector_store
        self.event_logger = event_logger
        self.ensemble = ReasoningEnsemble(
            model_name=model_name,
            similarity_threshold=similarity_threshold
        )

    @property
    def available_strategies(self) -> List[str]:
        """Return list of available strategy keys."""
        # Return unique canonical names
        return ["standard", "cot", "tot", "react", "self_reflection",
                "consistency", "decomposed", "least_to_most", "recursive"]

    def get_strategy_display_name(self, strategy: str) -> str:
        """Get human-readable name for strategy."""
        return self.STRATEGY_NAMES.get(strategy, strategy.title())

    def get_strategy_icon(self, strategy: str) -> str:
        """Get emoji icon for strategy."""
        return self.STRATEGY_ICONS.get(strategy, "🤖")

    async def run(
        self,
        query: str,
        strategies: List[str],
        use_rag: bool = True,
        collection: str = "PDF",
        config: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        Run reasoning ensemble with optional RAG context.

        Args:
            query: User's question
            strategies: List of strategy names to run
            use_rag: Whether to retrieve RAG context first
            collection: Which collection to query ("PDF", "Web", "Repository", "General")
            config: Per-strategy configuration

        Returns:
            ReasoningResult with winner, all responses, execution trace, etc.
        """
        start_time = time.time()
        execution_trace = []
        rag_context = None

        def log_event(event_type: str, message: str, data: Optional[Dict] = None):
            event = ExecutionEvent(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                event_type=event_type,
                message=message,
                data=data
            )
            execution_trace.append(event)
            return event

        # Start
        log_event("start", f"Starting ensemble with {len(strategies)} strategies")

        # RAG retrieval
        augmented_query = query
        if use_rag and self.vector_store:
            log_event("rag", f"Retrieving context from {collection} Collection...")
            rag_context = await self._retrieve_context(query, collection)

            if rag_context and rag_context.get("chunks"):
                chunks_count = len(rag_context["chunks"])
                avg_score = rag_context.get("avg_score", 0)
                log_event("rag", f"Found {chunks_count} relevant chunks (score: {avg_score:.2f})",
                         {"chunks": chunks_count, "score": avg_score})
                augmented_query = self._build_augmented_prompt(query, rag_context)
            else:
                log_event("rag", "No relevant context found, proceeding without RAG")

        # Run ensemble
        log_event("strategy_start", "Launching strategies in parallel...")

        # Log each strategy start
        for strategy in strategies:
            icon = self.get_strategy_icon(strategy)
            name = self.get_strategy_display_name(strategy)
            log_event("strategy_start", f"{icon} {name}: Starting...")

        # Execute ensemble
        result = await self.ensemble.run(augmented_query, strategies, config)

        # Log completions
        for resp in result["all_responses"]:
            icon = self.get_strategy_icon(resp["strategy"])
            name = self.get_strategy_display_name(resp["strategy"])
            duration = resp["duration_ms"] / 1000
            if resp.get("error"):
                log_event("strategy_complete", f"❌ {name}: Failed", {"error": True})
            else:
                log_event("strategy_complete", f"✅ {name}: Complete ({duration:.1f}s)",
                         {"duration_ms": resp["duration_ms"]})

        # Log voting (if multiple strategies)
        if result["voting_details"]:
            log_event("voting", f"Clustering {len(result['all_responses'])} responses...")
            winner = result["winner"]
            icon = self.get_strategy_icon(winner["strategy"])
            name = self.get_strategy_display_name(winner["strategy"])
            log_event("voting", f"🏆 Winner: {name} ({winner['vote_count']}/{len(result['all_responses'])} votes)")

        total_duration = (time.time() - start_time) * 1000
        log_event("complete", f"Ensemble complete ({total_duration/1000:.1f}s total)")

        # Log to database
        if self.event_logger:
            await self._log_reasoning_event(
                query=query,
                strategies=strategies,
                result=result,
                rag_context=rag_context,
                use_rag=use_rag,
                collection=collection,
                total_duration_ms=total_duration
            )

        return ReasoningResult(
            winner=result["winner"],
            all_responses=result["all_responses"],
            execution_trace=execution_trace,
            rag_context=rag_context,
            total_duration_ms=total_duration,
            voting_details=result["voting_details"]
        )

    async def run_with_streaming(
        self,
        query: str,
        strategies: List[str],
        use_rag: bool = True,
        collection: str = "PDF",
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """
        Run ensemble with streaming execution events for real-time UI updates.

        Yields ExecutionEvent objects as they occur.
        Final event has event_type="result" with full ReasoningResult in data.
        """
        start_time = time.time()
        rag_context = None

        def make_event(event_type: str, message: str, data: Optional[Dict] = None) -> ExecutionEvent:
            return ExecutionEvent(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                event_type=event_type,
                message=message,
                data=data
            )

        # Start
        yield make_event("start", f"Starting ensemble with {len(strategies)} strategies")

        # RAG retrieval
        augmented_query = query
        if use_rag and self.vector_store:
            yield make_event("rag", f"Retrieving context from {collection} Collection...")
            rag_context = await self._retrieve_context(query, collection)

            if rag_context and rag_context.get("chunks"):
                chunks_count = len(rag_context["chunks"])
                avg_score = rag_context.get("avg_score", 0)
                yield make_event("rag", f"Found {chunks_count} relevant chunks (score: {avg_score:.2f})")
                augmented_query = self._build_augmented_prompt(query, rag_context)
            else:
                yield make_event("rag", "No relevant context found")

        # Strategy execution
        yield make_event("strategy_start", "Launching strategies in parallel...")

        for strategy in strategies:
            icon = self.get_strategy_icon(strategy)
            name = self.get_strategy_display_name(strategy)
            yield make_event("strategy_start", f"{icon} {name}: Starting...")

        # Run ensemble
        result = await self.ensemble.run(augmented_query, strategies, config)

        # Yield completions
        for resp in result["all_responses"]:
            icon = self.get_strategy_icon(resp["strategy"])
            name = self.get_strategy_display_name(resp["strategy"])
            duration = resp["duration_ms"] / 1000
            yield make_event("strategy_complete", f"✅ {name}: Complete ({duration:.1f}s)")

        # Voting
        if result["voting_details"]:
            yield make_event("voting", f"Clustering {len(result['all_responses'])} responses...")
            winner = result["winner"]
            name = self.get_strategy_display_name(winner["strategy"])
            yield make_event("voting", f"🏆 Winner: {name} ({winner['vote_count']} votes)")

        total_duration = (time.time() - start_time) * 1000
        yield make_event("complete", f"Ensemble complete ({total_duration/1000:.1f}s)")

        # Final result
        final_result = ReasoningResult(
            winner=result["winner"],
            all_responses=result["all_responses"],
            execution_trace=[],  # Already streamed
            rag_context=rag_context,
            total_duration_ms=total_duration,
            voting_details=result["voting_details"]
        )

        yield make_event("result", "Final result", {"result": final_result})

    async def _retrieve_context(self, query: str, collection: str) -> Optional[Dict[str, Any]]:
        """Retrieve relevant context from vector store."""
        if not self.vector_store:
            return None

        try:
            # Map collection names
            collection_map = {
                "PDF": "pdf_collection",
                "Web": "web_collection",
                "Repository": "repo_collection",
                "General": "general_knowledge"
            }
            collection_name = collection_map.get(collection, "pdf_collection")

            # Query vector store
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.vector_store.query(query, collection_name=collection_name, n_results=5)
            )

            if not results:
                return None

            # Format results
            chunks = []
            scores = []
            sources = set()

            for doc in results:
                chunks.append({
                    "content": doc.get("content", doc.get("text", "")),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0)
                })
                scores.append(doc.get("score", 0))
                if "source" in doc.get("metadata", {}):
                    sources.add(doc["metadata"]["source"])

            return {
                "chunks": chunks,
                "sources": list(sources),
                "avg_score": sum(scores) / len(scores) if scores else 0
            }

        except Exception as e:
            print(f"Error retrieving RAG context: {e}")
            return None

    def _build_augmented_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build prompt with RAG context."""
        context_text = "\n\n".join([
            f"[Source: {c['metadata'].get('source', 'unknown')}]\n{c['content']}"
            for c in context.get("chunks", [])
        ])

        return f"""Use the following context to answer the question. If the context doesn't contain relevant information, use your general knowledge.

Context:
{context_text}

Question: {query}

Answer:"""

    async def _log_reasoning_event(
        self,
        query: str,
        strategies: List[str],
        result: Dict[str, Any],
        rag_context: Optional[Dict[str, Any]],
        use_rag: bool,
        collection: str,
        total_duration_ms: float
    ):
        """Log reasoning event to database."""
        if not self.event_logger:
            return

        try:
            import json

            self.event_logger.log_reasoning_event(
                query_text=query,
                strategies_requested=strategies,
                winner_strategy=result["winner"]["strategy"],
                winner_response=result["winner"]["response"],
                vote_count=result["winner"]["vote_count"],
                all_responses=result["all_responses"],
                rag_enabled=use_rag,
                collection_used=collection if use_rag else None,
                chunks_retrieved=len(rag_context["chunks"]) if rag_context else 0,
                total_duration_ms=total_duration_ms,
                config=None,
                status="success"
            )
        except Exception as e:
            print(f"Error logging reasoning event: {e}")
```

**Step 4: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/src/reasoning/
git commit -m "feat: add RAGReasoningEnsemble wrapper

- Wraps agent_reasoning.ReasoningEnsemble with RAG context
- Adds streaming execution trace for real-time UI
- Integrates with OraDBEventLogger for database logging
- Provides strategy icons and display names for UI"
```

---

### Task 2.3: Add REASONING_EVENTS table to OraDBEventLogger

**Files:**
- Modify: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/OraDBEventLogger.py`

**Step 1: Add table creation**

Add after line 142 (after `sql_query_events`):

```python
        # Reasoning Events Table - tracks reasoning ensemble executions
        sql_reasoning_events = """
        CREATE TABLE IF NOT EXISTS REASONING_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            query_text CLOB,
            strategies_requested CLOB,
            strategies_completed CLOB,
            winner_strategy VARCHAR2(50),
            winner_response CLOB,
            vote_count NUMBER,
            total_strategies NUMBER,
            similarity_threshold NUMBER,
            all_responses CLOB,
            rag_enabled NUMBER(1),
            collection_used VARCHAR2(200),
            chunks_retrieved NUMBER,
            total_duration_ms NUMBER,
            parallel_execution NUMBER(1),
            config_json CLOB,
            status VARCHAR2(50),
            error_message CLOB
        )
        """
```

Add to the try block (after line 150):

```python
            self.cursor.execute(sql_reasoning_events)
```

**Step 2: Add logging method**

Add after `log_query_event` method (around line 368):

```python
    def log_reasoning_event(
        self,
        query_text: str,
        strategies_requested: List[str],
        winner_strategy: str,
        winner_response: str,
        vote_count: int,
        all_responses: List[Dict[str, Any]],
        rag_enabled: bool = False,
        collection_used: Optional[str] = None,
        chunks_retrieved: int = 0,
        total_duration_ms: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Log a reasoning ensemble execution event"""
        event_id = f"reasoning_{uuid.uuid4().hex}"

        try:
            strategies_json = json.dumps(strategies_requested)
            all_responses_json = json.dumps(all_responses)
            config_json = json.dumps(config) if config else None

            sql = """
            INSERT INTO REASONING_EVENTS
            (event_id, query_text, strategies_requested, winner_strategy, winner_response,
             vote_count, total_strategies, all_responses, rag_enabled, collection_used,
             chunks_retrieved, total_duration_ms, parallel_execution, config_json, status, error_message)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16)
            """

            self.cursor.execute(sql, (
                event_id,
                query_text,
                strategies_json,
                winner_strategy,
                winner_response,
                vote_count,
                len(strategies_requested),
                all_responses_json,
                1 if rag_enabled else 0,
                collection_used,
                chunks_retrieved,
                total_duration_ms,
                1,  # parallel_execution always true for ensemble
                config_json,
                status,
                error_message
            ))
            self.connection.commit()

            print(f"[EventLogger] Reasoning event logged: {event_id} - {winner_strategy}")
            return event_id

        except Exception as e:
            print(f"[EventLogger] Error logging reasoning event: {str(e)}")
            return event_id
```

**Step 3: Update get_events method**

Add "reasoning" to the `table_map` dictionary (around line 379):

```python
        table_map = {
            "a2a": "A2A_EVENTS",
            "api": "API_EVENTS",
            "model": "MODEL_EVENTS",
            "document": "DOCUMENT_EVENTS",
            "query": "QUERY_EVENTS",
            "reasoning": "REASONING_EVENTS"
        }
```

**Step 4: Update get_statistics method**

Add after line 458:

```python
            stats["reasoning_events"] = self.get_event_count("reasoning")
```

**Step 5: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/src/OraDBEventLogger.py
git commit -m "feat: add REASONING_EVENTS table for ensemble logging

- New table tracks reasoning ensemble executions
- Stores all strategy responses and voting results
- Includes RAG context metadata
- Integrated with existing event logging infrastructure"
```

---

## Phase 3: A2A Protocol Integration

### Task 3.1: Create reasoning agent cards

**Files:**
- Create: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/reasoning_agent_cards.py`

**Step 1: Create file**

```python
"""
Agent cards for reasoning strategies.

Enables A2A discovery of all reasoning agents.
"""

from typing import Dict, List, Any


def get_reasoning_ensemble_card(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Get agent card for the reasoning ensemble orchestrator."""
    return {
        "agent_id": "reasoning_ensemble_v1",
        "name": "Reasoning Ensemble Orchestrator",
        "version": "1.0.0",
        "description": "Executes multiple reasoning strategies in parallel and aggregates via majority voting",
        "capabilities": [
            {
                "name": "reasoning.execute",
                "description": "Run ensemble of reasoning strategies with voting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The question to answer"},
                        "strategies": {"type": "array", "items": {"type": "string"}, "description": "List of strategy names"},
                        "use_rag": {"type": "boolean", "description": "Whether to use RAG context"},
                        "collection": {"type": "string", "description": "Collection to query (PDF, Web, Repository, General)"},
                        "config": {"type": "object", "description": "Per-strategy configuration"}
                    },
                    "required": ["query", "strategies"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "winner": {"type": "object"},
                        "all_responses": {"type": "array"},
                        "total_duration_ms": {"type": "number"}
                    }
                }
            },
            {
                "name": "reasoning.list",
                "description": "List available reasoning strategies",
                "input_schema": {"type": "object", "properties": {}},
                "output_schema": {"type": "array", "items": {"type": "string"}}
            }
        ],
        "endpoints": {
            "base_url": base_url,
            "authentication": {"type": "none"}
        },
        "metadata": {
            "type": "orchestrator",
            "strategies_available": 9
        }
    }


def get_strategy_agent_card(
    strategy_key: str,
    base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Get agent card for a specific reasoning strategy."""

    STRATEGY_INFO = {
        "standard": {
            "name": "Standard Generator",
            "description": "Direct LLM generation without reasoning enhancement (baseline)",
            "best_for": ["simple_queries", "baseline"],
            "params": {}
        },
        "cot": {
            "name": "Chain-of-Thought Reasoner",
            "description": "Step-by-step reasoning using Chain-of-Thought prompting (Wei et al. 2022)",
            "best_for": ["math", "logic", "explanations"],
            "params": {}
        },
        "tot": {
            "name": "Tree of Thoughts Explorer",
            "description": "Explores multiple reasoning branches using BFS (Yao et al. 2023)",
            "best_for": ["complex_riddles", "strategy"],
            "params": {"depth": 3, "width": 2}
        },
        "react": {
            "name": "ReAct Agent",
            "description": "Interleaves reasoning and tool usage (Yao et al. 2022)",
            "best_for": ["fact_checking", "calculations"],
            "params": {},
            "tools": ["web_search", "calculate"]
        },
        "self_reflection": {
            "name": "Self-Reflection Agent",
            "description": "Draft → Critique → Refine loop (Shinn et al. 2023)",
            "best_for": ["creative_writing", "high_accuracy"],
            "params": {"max_turns": 3}
        },
        "consistency": {
            "name": "Self-Consistency Voter",
            "description": "Generates multiple samples and votes for best answer (Wang et al. 2022)",
            "best_for": ["diverse_problems"],
            "params": {"samples": 3}
        },
        "decomposed": {
            "name": "Problem Decomposer",
            "description": "Breaks complex queries into sub-tasks (Khot et al. 2022)",
            "best_for": ["planning", "long_form"],
            "params": {}
        },
        "least_to_most": {
            "name": "Least-to-Most Reasoner",
            "description": "Solves from simplest to most complex (Zhou et al. 2022)",
            "best_for": ["complex_reasoning"],
            "params": {}
        },
        "recursive": {
            "name": "Recursive LM Agent",
            "description": "Recursively processes using Python REPL",
            "best_for": ["long_context"],
            "params": {}
        }
    }

    info = STRATEGY_INFO.get(strategy_key, {
        "name": strategy_key.title(),
        "description": f"Reasoning strategy: {strategy_key}",
        "best_for": [],
        "params": {}
    })

    return {
        "agent_id": f"reasoning_{strategy_key}_v1",
        "name": info["name"],
        "version": "1.0.0",
        "description": info["description"],
        "capabilities": [
            {
                "name": "reasoning.strategy",
                "description": f"Execute {info['name']} reasoning",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "config": {"type": "object"}
                    },
                    "required": ["query"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "duration_ms": {"type": "number"}
                    }
                }
            }
        ],
        "endpoints": {
            "base_url": base_url,
            "authentication": {"type": "none"}
        },
        "metadata": {
            "type": "strategy",
            "strategy_key": strategy_key,
            "best_for": info["best_for"],
            "params": info["params"]
        }
    }


def get_all_reasoning_agent_cards(base_url: str = "http://localhost:8000") -> Dict[str, Dict[str, Any]]:
    """Get all reasoning agent cards."""
    cards = {}

    # Ensemble orchestrator
    ensemble_card = get_reasoning_ensemble_card(base_url)
    cards[ensemble_card["agent_id"]] = ensemble_card

    # Individual strategies
    strategies = ["standard", "cot", "tot", "react", "self_reflection",
                  "consistency", "decomposed", "least_to_most", "recursive"]

    for strategy in strategies:
        card = get_strategy_agent_card(strategy, base_url)
        cards[card["agent_id"]] = card

    return cards


def get_reasoning_agent_card_by_id(agent_id: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Get a specific reasoning agent card by ID."""
    all_cards = get_all_reasoning_agent_cards(base_url)
    return all_cards.get(agent_id)
```

**Step 2: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/src/reasoning_agent_cards.py
git commit -m "feat: add reasoning agent cards for A2A discovery

- Ensemble orchestrator card with reasoning.execute capability
- Individual strategy cards with reasoning.strategy capability
- Strategy metadata including best_for and configurable params"
```

---

### Task 3.2: Add reasoning methods to A2A handler

**Files:**
- Modify: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/src/a2a_handler.py`

**Step 1: Add imports at top of file**

Add after other imports (around line 10):

```python
from .reasoning.rag_ensemble import RAGReasoningEnsemble
from .reasoning_agent_cards import get_all_reasoning_agent_cards, get_reasoning_agent_card_by_id
```

**Step 2: Update __init__ to include reasoning methods**

Add to the `self.methods` dict (around line 53):

```python
            # Reasoning methods
            "reasoning.execute": self.handle_reasoning_execute,
            "reasoning.strategy": self.handle_reasoning_strategy,
            "reasoning.list": self.handle_reasoning_list,
```

**Step 3: Add reasoning ensemble instance**

Add after `self._specialized_agents = {}` (around line 40):

```python
        # Initialize reasoning ensemble
        self._reasoning_ensemble = None
```

**Step 4: Add lazy initialization method**

Add after `_load_specialized_agent_model` method:

```python
    def _get_reasoning_ensemble(self) -> RAGReasoningEnsemble:
        """Lazy initialize reasoning ensemble."""
        if self._reasoning_ensemble is None:
            model = self._load_specialized_agent_model()
            self._reasoning_ensemble = RAGReasoningEnsemble(
                model_name=model,
                vector_store=self.vector_store,
                event_logger=self.event_logger
            )
        return self._reasoning_ensemble
```

**Step 5: Add handler methods**

Add after `handle_agent_query` method:

```python
    async def handle_reasoning_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reasoning.execute requests - run ensemble with voting."""
        import time
        start_time = time.time()

        query = params.get("query", "")
        strategies = params.get("strategies", ["cot"])
        use_rag = params.get("use_rag", True)
        collection = params.get("collection", "PDF")
        config = params.get("config", {})

        if not query:
            return {"error": "Query is required"}

        ensemble = self._get_reasoning_ensemble()
        result = await ensemble.run(
            query=query,
            strategies=strategies,
            use_rag=use_rag,
            collection=collection,
            config=config
        )

        # Log A2A event
        if self.event_logger:
            duration_ms = (time.time() - start_time) * 1000
            self.event_logger.log_a2a_event(
                agent_id="reasoning_ensemble_v1",
                agent_name="Reasoning Ensemble",
                method="reasoning.execute",
                user_prompt=query,
                response=result.winner["response"],
                metadata={
                    "strategies": strategies,
                    "winner": result.winner["strategy"],
                    "use_rag": use_rag
                },
                duration_ms=duration_ms,
                status="success"
            )

        return {
            "winner": result.winner,
            "all_responses": result.all_responses,
            "execution_trace": [
                {"timestamp": e.timestamp, "type": e.event_type, "message": e.message}
                for e in result.execution_trace
            ],
            "rag_context": result.rag_context,
            "total_duration_ms": result.total_duration_ms,
            "voting_details": result.voting_details
        }

    async def handle_reasoning_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reasoning.strategy requests - run single strategy."""
        query = params.get("query", "")
        strategy = params.get("strategy", "cot")
        config = params.get("config", {})

        if not query:
            return {"error": "Query is required"}

        ensemble = self._get_reasoning_ensemble()
        result = await ensemble.run(
            query=query,
            strategies=[strategy],
            use_rag=False,  # Single strategy typically without RAG
            config={strategy: config} if config else None
        )

        return {
            "strategy": strategy,
            "response": result.winner["response"],
            "duration_ms": result.total_duration_ms
        }

    async def handle_reasoning_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reasoning.list requests - list available strategies."""
        ensemble = self._get_reasoning_ensemble()
        strategies = ensemble.available_strategies

        return {
            "strategies": strategies,
            "count": len(strategies),
            "details": {
                s: {
                    "name": ensemble.get_strategy_display_name(s),
                    "icon": ensemble.get_strategy_icon(s)
                }
                for s in strategies
            }
        }
```

**Step 6: Update _register_specialized_agents to include reasoning agents**

Add at the end of `_register_specialized_agents` method (before the final except block):

```python
            # Register reasoning agents
            reasoning_cards = get_all_reasoning_agent_cards(
                self.agent_endpoints.get('planner_url', 'http://localhost:8000')
            )

            for agent_id, card_data in reasoning_cards.items():
                try:
                    capabilities = []
                    for cap_data in card_data.get("capabilities", []):
                        capability = AgentCapability(
                            name=cap_data["name"],
                            description=cap_data["description"],
                            input_schema=cap_data.get("input_schema", {}),
                            output_schema=cap_data.get("output_schema", {})
                        )
                        capabilities.append(capability)

                    endpoints_data = card_data.get("endpoints", {})
                    endpoints = AgentEndpoint(
                        base_url=endpoints_data.get("base_url", "http://localhost:8000"),
                        authentication=endpoints_data.get("authentication", {})
                    )

                    agent_card = AgentCard(
                        agent_id=card_data["agent_id"],
                        name=card_data["name"],
                        version=card_data["version"],
                        description=card_data["description"],
                        capabilities=capabilities,
                        endpoints=endpoints,
                        metadata=card_data.get("metadata", {})
                    )

                    success = self.agent_registry.register_agent(agent_card)
                    if success:
                        logger.info(f"Registered reasoning agent: {agent_id}")

                except Exception as e:
                    logger.error(f"Error registering reasoning agent {agent_id}: {str(e)}")

            logger.info(f"Reasoning agent registration complete")
```

**Step 7: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/src/a2a_handler.py
git commit -m "feat: add reasoning A2A methods

- reasoning.execute: Run ensemble with voting
- reasoning.strategy: Run single strategy
- reasoning.list: List available strategies
- Register all reasoning agents for A2A discovery"
```

---

## Phase 4: Unified Chat UI

### Task 4.1: Create unified chat UI in Gradio

**Files:**
- Modify: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/gradio_app.py`

This is a large modification. The key changes are:

1. Remove separate chat tabs (Standard Chat, CoT Chat, A2A Chat)
2. Create single unified chat with:
   - Settings bar (model, RAG toggle, collection)
   - Strategy multi-select with Advanced panel
   - Execution trace display
   - Strategy responses accordion
   - Final answer display

**Step 1: Add imports at top of file**

Add after existing imports:

```python
from src.reasoning.rag_ensemble import RAGReasoningEnsemble, ExecutionEvent, ReasoningResult
```

**Step 2: Initialize reasoning ensemble**

Add after `local_agent` initialization (around line 80):

```python
# Initialize reasoning ensemble
reasoning_ensemble = None
try:
    reasoning_ensemble = RAGReasoningEnsemble(
        model_name="gemma3:270m",
        vector_store=vector_store,
        event_logger=None  # Will be set later if available
    )
    print("Reasoning ensemble initialized")
except Exception as e:
    print(f"Could not initialize reasoning ensemble: {str(e)}")
```

**Step 3: Add chat function**

Add new function for unified chat:

```python
async def unified_chat(
    message: str,
    history: list,
    model: str,
    use_rag: bool,
    collection: str,
    strategies: list,
    tot_depth: int,
    consistency_samples: int,
    reflection_turns: int
):
    """
    Unified chat function that handles reasoning ensemble.

    Returns: (history, execution_trace, strategy_responses, final_answer)
    """
    if not message.strip():
        return history, "", "", ""

    if not strategies:
        strategies = ["cot"]  # Default to CoT

    # Build config from advanced settings
    config = {}
    if "tot" in strategies:
        config["tot"] = {"depth": tot_depth}
    if "consistency" in strategies:
        config["consistency"] = {"samples": consistency_samples}
    if "self_reflection" in strategies:
        config["self_reflection"] = {"max_turns": reflection_turns}

    # Run ensemble
    if reasoning_ensemble:
        result = await reasoning_ensemble.run(
            query=message,
            strategies=strategies,
            use_rag=use_rag,
            collection=collection,
            config=config
        )

        # Format execution trace
        trace_lines = []
        for event in result.execution_trace:
            trace_lines.append(f"{event.timestamp} │ {event.message}")
        execution_trace = "\n".join(trace_lines)

        # Format strategy responses
        response_blocks = []
        for resp in result.all_responses:
            is_winner = resp["strategy"] == result.winner["strategy"]
            icon = reasoning_ensemble.get_strategy_icon(resp["strategy"])
            name = reasoning_ensemble.get_strategy_display_name(resp["strategy"])
            duration = resp["duration_ms"] / 1000

            winner_badge = "🏆 " if is_winner else ""
            vote_info = f" ({result.winner['vote_count']} votes)" if is_winner and result.voting_details else ""

            block = f"""### {winner_badge}{icon} {name}{vote_info} ⏱️ {duration:.1f}s

{resp["response"][:500]}{"..." if len(resp["response"]) > 500 else ""}
"""
            response_blocks.append(block)

        strategy_responses = "\n---\n".join(response_blocks)

        # Format final answer
        sources_text = ""
        if result.rag_context and result.rag_context.get("sources"):
            sources_text = "\n\n📚 **Sources:** " + ", ".join(result.rag_context["sources"])

        final_answer = result.winner["response"] + sources_text

        # Update history
        history.append((message, final_answer))

        return history, execution_trace, strategy_responses, final_answer
    else:
        # Fallback to simple response
        history.append((message, "Reasoning ensemble not initialized"))
        return history, "", "", "Reasoning ensemble not initialized"
```

**Step 4: Create the unified chat interface**

Replace the existing chat tabs with a unified interface. This involves restructuring the Gradio Blocks layout. The full implementation is extensive - here's the key structure:

```python
def create_unified_chat_tab():
    """Create the unified chat interface."""
    with gr.Column():
        # Settings bar
        with gr.Row():
            model_dropdown = gr.Dropdown(
                choices=["gemma3:270m", "llama3", "mistral"],
                value="gemma3:270m",
                label="Model"
            )
            rag_toggle = gr.Checkbox(value=True, label="RAG Enabled")
            collection_dropdown = gr.Dropdown(
                choices=["PDF", "Web", "Repository", "General"],
                value="PDF",
                label="Collection"
            )

        # Strategy selector
        with gr.Row():
            strategy_checkboxes = gr.CheckboxGroup(
                choices=[
                    ("Chain-of-Thought", "cot"),
                    ("Tree of Thoughts", "tot"),
                    ("ReAct", "react"),
                    ("Self-Reflection", "self_reflection"),
                    ("Self-Consistency", "consistency"),
                    ("Decomposed", "decomposed"),
                    ("Least-to-Most", "least_to_most"),
                    ("Recursive", "recursive"),
                    ("Standard", "standard")
                ],
                value=["cot"],
                label="Reasoning Strategies"
            )

        # Advanced settings (collapsible)
        with gr.Accordion("Advanced Settings", open=False):
            tot_depth = gr.Slider(1, 5, value=3, step=1, label="ToT Depth")
            consistency_samples = gr.Slider(1, 7, value=3, step=1, label="Consistency Samples")
            reflection_turns = gr.Slider(1, 5, value=3, step=1, label="Reflection Turns")

        # Chat area
        chatbot = gr.Chatbot(height=300, label="Chat")

        # Execution trace (collapsible)
        with gr.Accordion("🔄 Execution Trace", open=True):
            execution_trace = gr.Textbox(
                lines=10,
                label="",
                interactive=False
            )

        # Strategy responses (collapsible)
        with gr.Accordion("📊 Strategy Responses", open=False):
            strategy_responses = gr.Markdown()

        # Final answer
        with gr.Row():
            final_answer = gr.Markdown(label="💬 Final Answer")

        # Input
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Type your message...",
                show_label=False,
                scale=4
            )
            send_btn = gr.Button("Send", variant="primary")
            clear_btn = gr.Button("Clear")

        # Wire up events
        send_btn.click(
            fn=unified_chat,
            inputs=[
                msg_input, chatbot, model_dropdown, rag_toggle,
                collection_dropdown, strategy_checkboxes,
                tot_depth, consistency_samples, reflection_turns
            ],
            outputs=[chatbot, execution_trace, strategy_responses, final_answer]
        ).then(
            fn=lambda: "",
            outputs=msg_input
        )

        clear_btn.click(
            fn=lambda: ([], "", "", ""),
            outputs=[chatbot, execution_trace, strategy_responses, final_answer]
        )

    return chatbot
```

**Note:** The full implementation requires careful integration with the existing gradio_app.py structure. The above provides the key patterns - the actual implementation will need to:

1. Preserve existing functionality (Model Management, Document Processing tabs)
2. Remove old chat tabs
3. Add the unified chat as a new tab
4. Wire up all the event handlers properly

**Step 5: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/gradio_app.py
git commit -m "feat: add unified chat UI with reasoning ensemble

- Single chat interface with RAG toggle
- Multi-select strategy checkboxes
- Real-time execution trace display
- Collapsible strategy responses panel
- Advanced settings for strategy configuration"
```

---

## Phase 5: Testing and Documentation

### Task 5.1: Add integration tests

**Files:**
- Create: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/tests/test_reasoning.py`

**Step 1: Create test file**

```python
"""Integration tests for reasoning ensemble."""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

# Import after mocking to avoid initialization issues
import sys
sys.path.insert(0, '/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag')


class TestRAGReasoningEnsemble:
    """Test suite for RAGReasoningEnsemble."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        store = Mock()
        store.query.return_value = [
            {"content": "Test content", "metadata": {"source": "test.pdf"}, "score": 0.9}
        ]
        return store

    @pytest.fixture
    def ensemble(self, mock_vector_store):
        """Create ensemble with mocked dependencies."""
        from src.reasoning.rag_ensemble import RAGReasoningEnsemble

        return RAGReasoningEnsemble(
            model_name="gemma3:270m",
            vector_store=mock_vector_store,
            event_logger=None
        )

    def test_available_strategies(self, ensemble):
        """Test that all strategies are available."""
        strategies = ensemble.available_strategies

        assert "cot" in strategies
        assert "tot" in strategies
        assert "react" in strategies
        assert len(strategies) == 9

    def test_strategy_display_names(self, ensemble):
        """Test strategy display names."""
        assert ensemble.get_strategy_display_name("cot") == "Chain-of-Thought"
        assert ensemble.get_strategy_display_name("tot") == "Tree of Thoughts"

    def test_strategy_icons(self, ensemble):
        """Test strategy icons."""
        assert ensemble.get_strategy_icon("cot") == "🔗"
        assert ensemble.get_strategy_icon("tot") == "🌳"


class TestA2AReasoningMethods:
    """Test A2A reasoning method handlers."""

    @pytest.fixture
    def mock_handler(self):
        """Create mock A2A handler."""
        from src.a2a_handler import A2AHandler

        handler = Mock(spec=A2AHandler)
        handler.handle_reasoning_list = A2AHandler.handle_reasoning_list
        return handler

    @pytest.mark.asyncio
    async def test_reasoning_list(self):
        """Test reasoning.list method."""
        from src.reasoning.rag_ensemble import RAGReasoningEnsemble

        ensemble = RAGReasoningEnsemble(model_name="gemma3:270m")
        strategies = ensemble.available_strategies

        assert len(strategies) == 9
        assert "cot" in strategies


class TestReasoningAgentCards:
    """Test reasoning agent card generation."""

    def test_get_all_cards(self):
        """Test getting all reasoning agent cards."""
        from src.reasoning_agent_cards import get_all_reasoning_agent_cards

        cards = get_all_reasoning_agent_cards()

        # Should have ensemble + 9 strategies = 10 cards
        assert len(cards) == 10
        assert "reasoning_ensemble_v1" in cards
        assert "reasoning_cot_v1" in cards

    def test_ensemble_card_capabilities(self):
        """Test ensemble card has correct capabilities."""
        from src.reasoning_agent_cards import get_reasoning_ensemble_card

        card = get_reasoning_ensemble_card()

        assert card["agent_id"] == "reasoning_ensemble_v1"
        capability_names = [c["name"] for c in card["capabilities"]]
        assert "reasoning.execute" in capability_names
        assert "reasoning.list" in capability_names

    def test_strategy_card_metadata(self):
        """Test strategy cards have correct metadata."""
        from src.reasoning_agent_cards import get_strategy_agent_card

        card = get_strategy_agent_card("cot")

        assert card["metadata"]["type"] == "strategy"
        assert card["metadata"]["strategy_key"] == "cot"
        assert "math" in card["metadata"]["best_for"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

Run:
```bash
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag
pytest tests/test_reasoning.py -v
```

Expected: All tests PASS

**Step 3: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/tests/test_reasoning.py
git commit -m "test: add reasoning integration tests

- Test RAGReasoningEnsemble strategies and display names
- Test A2A reasoning method handlers
- Test reasoning agent card generation"
```

---

### Task 5.2: Update README

**Files:**
- Modify: `/home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag/README.md`

**Step 1: Add reasoning section**

Add after the Chain of Thought section:

```markdown
## 4. Advanced Reasoning Strategies

The system now supports multiple advanced reasoning strategies from the `agent-reasoning` library, which can be run individually or as an ensemble with majority voting.

### Available Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Chain-of-Thought (CoT)** | Step-by-step reasoning | Math, logic, explanations |
| **Tree of Thoughts (ToT)** | Explores multiple reasoning branches | Complex riddles, strategy |
| **ReAct** | Interleaves reasoning and tool usage | Fact-checking, calculations |
| **Self-Reflection** | Draft → Critique → Refine loop | Creative writing, accuracy |
| **Self-Consistency** | Generates multiple samples and votes | Diverse problems |
| **Decomposed** | Breaks complex queries into sub-tasks | Planning, long-form |
| **Least-to-Most** | Solves from simplest to complex | Complex reasoning |
| **Recursive** | Recursively processes content | Long context |

### Ensemble Voting

When multiple strategies are selected, they run in parallel and the system uses **majority voting** to select the best answer:

1. All selected strategies process the query simultaneously
2. Responses are clustered by semantic similarity
3. The largest cluster's response wins
4. If there's a tie, CoT is preferred as fallback

### Using Reasoning via CLI

```bash
# Run with single strategy
python -m src.local_rag_agent --query "Your question" --strategy cot

# Run with ensemble
python -m src.local_rag_agent --query "Your question" --strategies cot,tot,consistency
```

### Using Reasoning via A2A Protocol

```bash
# Run ensemble via A2A
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "reasoning.execute",
    "params": {
      "query": "What is machine learning?",
      "strategies": ["cot", "tot", "consistency"],
      "use_rag": true,
      "collection": "PDF"
    },
    "id": "1"
  }'

# List available strategies
curl -X POST http://localhost:8000/a2a \
  -d '{"jsonrpc": "2.0", "method": "reasoning.list", "params": {}, "id": "2"}'

# Discover reasoning agents
curl -X POST http://localhost:8000/a2a \
  -d '{"jsonrpc": "2.0", "method": "agent.discover", "params": {"capability": "reasoning.strategy"}, "id": "3"}'
```

### Unified Chat Interface

The Gradio interface now provides a unified chat with:

- **RAG Toggle**: Enable/disable document retrieval
- **Strategy Selection**: Multi-select checkboxes for strategies
- **Advanced Settings**: Configure ToT depth, consistency samples, etc.
- **Execution Trace**: Real-time view of strategy execution
- **Strategy Responses**: View all individual strategy outputs
- **Final Answer**: Winning response with sources
```

**Step 2: Commit**

```bash
cd /home/ubuntu/git/oracle-ai-developer-hub
git add apps/agentic_rag/README.md
git commit -m "docs: add reasoning strategies documentation

- Document all 9 reasoning strategies
- Explain ensemble voting mechanism
- Add CLI and A2A usage examples
- Describe unified chat interface features"
```

---

## Summary

### Commits Checklist

- [ ] Phase 1.1: Restructure agent-reasoning for PyPI
- [ ] Phase 1.2: Add ReasoningEnsemble class
- [ ] Phase 1.3: Test and build PyPI package
- [ ] Phase 2.1: Add agent-reasoning dependency
- [ ] Phase 2.2: Create RAGReasoningEnsemble wrapper
- [ ] Phase 2.3: Add REASONING_EVENTS table
- [ ] Phase 3.1: Create reasoning agent cards
- [ ] Phase 3.2: Add reasoning methods to A2A handler
- [ ] Phase 4.1: Create unified chat UI
- [ ] Phase 5.1: Add integration tests
- [ ] Phase 5.2: Update README

### Testing Commands

```bash
# Test agent-reasoning package
cd /home/ubuntu/git/agent-reasoning
pytest tests/ -v

# Test agentic_rag integration
cd /home/ubuntu/git/oracle-ai-developer-hub/apps/agentic_rag
pytest tests/test_reasoning.py -v

# Run the application
python gradio_app.py
```

### A2A Verification

```bash
# Start server
python -m src.main &

# Test reasoning.list
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "reasoning.list", "params": {}, "id": "1"}'

# Test agent discovery
curl -X POST http://localhost:8000/a2a \
  -d '{"jsonrpc": "2.0", "method": "agent.discover", "params": {"capability": "reasoning.execute"}, "id": "2"}'
```
