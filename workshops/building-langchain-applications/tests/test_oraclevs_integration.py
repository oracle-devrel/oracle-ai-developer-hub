"""Opt-in integration coverage for the checked-in corpus and OracleVS.

Run with a prepared local database and exported connection settings:
    set -a; source .env; set +a
    RUN_ORACLE_INTEGRATION=1 venv/bin/python -m unittest discover -s tests -p 'test_oraclevs_integration.py' -v

The test uses deterministic local embeddings, so it never uses an OpenAI key or
incurs embedding costs. It creates and removes only its own table.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import oracledb
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_oracledb.vectorstores import DistanceStrategy, OracleVS

from src.evaluation import citation_urls_are_retrieved, citations_from_documents

TABLE_NAME = "M3_RAG_INTEGRATION"
RUN_INTEGRATION = os.environ.get("RUN_ORACLE_INTEGRATION") == "1"


class TopicEmbeddings(Embeddings):
    """Small deterministic embeddings for database integration coverage only."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embedding(text)

    @staticmethod
    def _embedding(text: str) -> list[float]:
        normalized = text.lower()
        if "picasso" in normalized:
            return [1.0, 0.0, 0.0, 0.0]
        if "museum" in normalized:
            return [0.0, 1.0, 0.0, 0.0]
        if "history" in normalized:
            return [0.0, 0.0, 1.0, 0.0]
        return [0.0, 0.0, 0.0, 1.0]


@unittest.skipUnless(RUN_INTEGRATION, "set RUN_ORACLE_INTEGRATION=1 to run against a local Oracle database")
class OracleVSIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.connection = oracledb.connect(
            user=os.environ["ORACLE_USER"],
            password=os.environ["ORACLE_PASSWORD"],
            dsn=os.environ["ORACLE_DSN"],
        )
        records = [
            json.loads(line)
            for line in Path("data/releases/paris_dataset_v2026.1.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        cls.eval_cases = json.loads(Path("data/evals/rag_eval_v2026.1.json").read_text(encoding="utf-8"))["cases"]
        cls.documents = [
            Document(
                page_content=record["body"],
                metadata={
                    key: record[key]
                    for key in ("document_id", "title", "topic", "place", "source_url", "retrieved_at")
                },
            )
            for record in records
        ]
        for document in cls.documents:
            document.metadata["chunk_id"] = document.metadata["document_id"]
            document.metadata["corpus_version"] = "2026.1"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._drop_table_if_present()
        cls.connection.close()

    @classmethod
    def _drop_table_if_present(cls) -> None:
        with cls.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM user_tables WHERE table_name = :name", name=TABLE_NAME)
            if cursor.fetchone():
                cursor.execute(f"DROP TABLE {TABLE_NAME} PURGE")

    @classmethod
    def _rebuild_store(cls) -> OracleVS:
        cls._drop_table_if_present()
        return OracleVS.from_documents(
            cls.documents,
            TopicEmbeddings(),
            client=cls.connection,
            table_name=TABLE_NAME,
            distance_strategy=DistanceStrategy.COSINE,
        )

    def test_ingests_filters_cites_and_rebuilds_the_release(self) -> None:
        store = self._rebuild_store()
        museum_case = next(case for case in self.eval_cases if case["case_id"] == "museum-picasso-grounded")
        results = store.similarity_search_with_score(
            museum_case["question"],
            k=len(museum_case["expected_document_ids"]),
            filter=museum_case["filter"],
        )

        self.assertTrue(results)
        retrieved_documents = [document for document, _ in results]
        self.assertTrue(all(document.metadata["topic"] == "museum" for document in retrieved_documents))
        self.assertTrue(set(museum_case["expected_document_ids"]).issubset({document.metadata["document_id"] for document in retrieved_documents}))
        self.assertTrue(all(document.metadata["corpus_version"] == "2026.1" for document in retrieved_documents))
        citations = citations_from_documents(retrieved_documents)
        self.assertTrue(citation_urls_are_retrieved(citations, retrieved_documents))

        rebuilt_store = self._rebuild_store()
        rebuilt_results = rebuilt_store.similarity_search_with_score(
            "Which museum is in Paris?",
            k=1,
            filter={"topic": "museum"},
        )
        self.assertEqual(len(rebuilt_results), 1)


if __name__ == "__main__":
    unittest.main()
