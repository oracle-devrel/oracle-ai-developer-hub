"""Opt-in integration coverage for Oracle Agent Memory.

Run against the prepared Compose database with:

    set -a; source .env; set +a
    RUN_AGENT_MEMORY_INTEGRATION=1 venv/bin/python -m unittest tests.test_memory -v

The test uses synthetic preferences only, but it requires a funded
``OPENAI_API_KEY`` and incurs small real embedding API charges when enabled.
It creates one temporary thread, recreates the client and pool to prove
persistence, then deletes the thread. It is skipped by the default test run.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import unittest
import uuid

import oracledb
from oracleagentmemory.core import MemoryExtractionConfig
from oracleagentmemory.core.embedders.embedder import Embedder
from oracleagentmemory.core.llms.llm import Llm
from oracleagentmemory.core.oracleagentmemory import OracleAgentMemory

from src.config import load_settings


RUN_INTEGRATION = os.environ.get("RUN_AGENT_MEMORY_INTEGRATION") == "1"


@unittest.skipUnless(RUN_INTEGRATION, "set RUN_AGENT_MEMORY_INTEGRATION=1 to run against a local Oracle database")
class AgentMemoryIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings = load_settings()
        cls.user_id = f"m4-test-user-{uuid.uuid4().hex[:12]}"
        cls.thread_id = f"m4-test-thread-{uuid.uuid4().hex[:12]}"
        cls.pool = cls._create_pool(settings)
        cls.memory = cls._create_memory(settings, cls.pool, schema_policy="create_if_necessary")

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "memory"):
            cls.memory.delete_thread(cls.thread_id)
            cls.memory.close()
        if hasattr(cls, "pool"):
            cls.pool.close()

    @staticmethod
    def _create_pool(settings):
        return oracledb.create_pool(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            min=1,
            max=2,
            increment=1,
        )

    @staticmethod
    def _create_memory(settings, pool, *, schema_policy):
        return OracleAgentMemory(
            connection=pool,
            embedder=Embedder(model=settings.embedding_model, api_key=settings.openai_api_key),
            llm=Llm(model=settings.openai_model, api_key=settings.openai_api_key),
            memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
            schema_policy=schema_policy,
        )

    def test_memory_is_scoped_updated_deleted_and_persistent(self) -> None:
        settings = load_settings()
        thread = self.memory.create_thread(
            thread_id=self.thread_id,
            user_id=self.user_id,
            memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
        )
        thread.add_messages([{"role": "user", "content": "I prefer vegetarian food."}])
        memory_timestamp = datetime.now(timezone.utc).isoformat()
        memory_id = thread.add_memory(
            "User prefers vegetarian food.",
            memory_type="preference",
            memory_id=f"m4-test-memory-{uuid.uuid4().hex[:12]}",
            timestamp=memory_timestamp,
            metadata={"source": "explicit_user_statement"},
        )

        own_results = self.memory.search(
            "What food does this user prefer?",
            user_id=self.user_id,
            exact_user_match=True,
            record_types=["preference"],
            max_results=5,
        )
        other_user_results = self.memory.search(
            "What food does this user prefer?",
            user_id=f"m4-other-user-{uuid.uuid4().hex[:12]}",
            exact_user_match=True,
            record_types=["preference"],
            max_results=5,
        )
        self.assertTrue(any(result.id == memory_id for result in own_results))
        self.assertEqual(other_user_results, [])

        updated_id = thread.update_memory(memory_id, "User prefers vegetarian and North African food.")
        self.assertEqual(updated_id, memory_id)

        self.memory.close()
        self.pool.close()
        reopened_pool = self._create_pool(settings)
        reopened_memory = self._create_memory(settings, reopened_pool, schema_policy="require_existing")
        type(self).pool = reopened_pool
        type(self).memory = reopened_memory
        reopened_thread = reopened_memory.get_thread(
            self.thread_id,
            memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
        )
        reopened_results = self.memory.search(
            "What food does this user prefer now?",
            user_id=self.user_id,
            exact_user_match=True,
            record_types=["preference"],
            max_results=5,
        )
        self.assertEqual(reopened_thread.thread_id, self.thread_id)
        self.assertTrue(any(result.id == memory_id and "North African" in result.content for result in reopened_results))

        self.assertEqual(reopened_thread.delete_memory(memory_id), 1)
        self.assertEqual(
            self.memory.search(
                "What food does this user prefer now?",
                user_id=self.user_id,
                exact_user_match=True,
                record_types=["preference"],
                max_results=5,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
