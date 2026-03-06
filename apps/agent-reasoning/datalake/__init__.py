"""
Datalake: Oracle 26ai DB storage and querying for agent reasoning stack traces.

Stores full reasoning sessions (events, metrics, comparisons) in Oracle Database
with JSON column support, enabling rich querying and replay of reasoning strategies.

Usage:
    from datalake import ReasoningStore, get_db_config
    from datalake.models import ReasoningSession, ReasoningEvent, ReasoningMetric

    config = get_db_config()
    store = ReasoningStore(config)
    session_id = store.create_session("What is 2+2?", "cot", "gemma3:latest")
"""

from datalake.config import get_db_config, DatabaseConfig
from datalake.store import ReasoningStore
from datalake.models import (
    Base,
    ReasoningSession,
    ReasoningEvent,
    ReasoningMetric,
    ReasoningComparison,
)

__version__ = "0.1.0"

__all__ = [
    "ReasoningStore",
    "get_db_config",
    "DatabaseConfig",
    "Base",
    "ReasoningSession",
    "ReasoningEvent",
    "ReasoningMetric",
    "ReasoningComparison",
]
