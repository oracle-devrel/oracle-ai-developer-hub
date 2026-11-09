from __future__ import annotations

import unittest
from dataclasses import dataclass

from src.evaluation import citation_urls_are_retrieved, citations_from_documents, grounding_decision


@dataclass
class Document:
    metadata: dict[str, str]


class CitationTest(unittest.TestCase):
    def test_citations_are_derived_only_from_retrieved_documents(self) -> None:
        documents = [
            Document(
                {
                    "title": "Louvre",
                    "source_url": "https://example.test/louvre",
                    "document_id": "louvre",
                    "chunk_id": "louvre#chunk-000",
                }
            )
        ]
        citations = citations_from_documents(documents)
        self.assertTrue(citation_urls_are_retrieved(citations, documents))
        self.assertFalse(
            citation_urls_are_retrieved(
                [{**citations[0], "url": "https://example.test/invented"}], documents
            )
        )
        self.assertFalse(
            citation_urls_are_retrieved([{**citations[0], "chunk_id": "not-retrieved"}], documents)
        )
        self.assertFalse(citation_urls_are_retrieved([], documents))

    def test_shared_source_urls_do_not_collapse_document_identity(self) -> None:
        documents = [
            Document(
                {
                    "title": "Catalog",
                    "source_url": "https://example.test/shared",
                    "document_id": "catalog",
                    "chunk_id": "catalog#chunk-000",
                }
            ),
            Document(
                {
                    "title": "Provenance",
                    "source_url": "https://example.test/shared",
                    "document_id": "provenance",
                    "chunk_id": "provenance#chunk-000",
                }
            ),
        ]

        citations = citations_from_documents(documents)

        self.assertEqual(
            [citation["chunk_id"] for citation in citations],
            ["catalog#chunk-000", "provenance#chunk-000"],
        )
        self.assertTrue(citation_urls_are_retrieved(citations, documents))
        fabricated = {
            "title": "Catalog",
            "url": "https://example.test/shared",
            "chunk_id": "never-retrieved",
        }
        self.assertFalse(citation_urls_are_retrieved([fabricated], documents))

    def test_legacy_documents_use_document_id_as_chunk_identity(self) -> None:
        document = Document(
            {
                "title": "Louvre",
                "source_url": "https://example.test/louvre",
                "document_id": "louvre",
            }
        )
        citations = citations_from_documents([document])
        self.assertEqual(citations[0]["chunk_id"], "louvre")
        self.assertTrue(citation_urls_are_retrieved(citations, [document]))


class GroundingDecisionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.document = Document(
            {
                "title": "Louvre",
                "source_url": "https://example.test/louvre",
                "document_id": "louvre",
                "chunk_id": "louvre#chunk-000",
            }
        )

    def test_empty_results_abstain(self) -> None:
        decision = grounding_decision([], max_distance=0.55)
        self.assertFalse(decision["grounded"])
        self.assertIsNone(decision["supporting_document"])
        self.assertIn("no matching evidence", decision["uncertainty"])

    def test_weak_results_abstain(self) -> None:
        decision = grounding_decision([(self.document, 0.56)], max_distance=0.55)
        self.assertFalse(decision["grounded"])
        self.assertIn("too distant", decision["uncertainty"])

    def test_boundary_and_stronger_results_are_eligible(self) -> None:
        boundary = grounding_decision([(self.document, 0.55)], max_distance=0.55)
        stronger = grounding_decision([(self.document, 0.40)], max_distance=0.55)
        self.assertTrue(boundary["grounded"])
        self.assertTrue(stronger["grounded"])
        self.assertIsNone(boundary["uncertainty"])

    def test_unsorted_results_choose_closest_document(self) -> None:
        farther = Document(
            {
                "title": "Farther",
                "source_url": "https://example.test/farther",
                "document_id": "farther",
                "chunk_id": "farther#chunk-000",
            }
        )
        decision = grounding_decision([(farther, 0.50), (self.document, 0.20)], max_distance=0.55)
        self.assertTrue(decision["grounded"])
        self.assertIs(decision["supporting_document"], self.document)
        self.assertEqual(decision["best_score"], 0.20)
