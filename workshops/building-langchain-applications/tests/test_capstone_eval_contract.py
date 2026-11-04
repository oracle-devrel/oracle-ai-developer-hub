from __future__ import annotations

import json
import unittest
from pathlib import Path


class CapstoneEvaluationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evaluation = json.loads(
            Path("data/evals/capstone_eval_v2026.1.json").read_text(encoding="utf-8")
        )
        cls.records = {
            json.loads(line)["document_id"]
            for line in Path("data/releases/paris_dataset_v2026.1.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        }

    def test_fixture_is_versioned_and_references_only_release_records(self) -> None:
        self.assertEqual(self.evaluation["corpus_name"], "Paris Dataset")
        self.assertEqual(self.evaluation["corpus_version"], "2026.1")
        self.assertGreaterEqual(len(self.evaluation["cases"]), 4)
        for case in self.evaluation["cases"]:
            self.assertTrue(case["case_id"])
            self.assertTrue(case["question"])
            self.assertIn(
                case["expected_behavior"],
                {
                    "grounded_personalized",
                    "grounded_without_personalization",
                    "abstain_or_uncertainty",
                    "ignore_untrusted_instruction",
                },
            )
            self.assertTrue(set(case["expected_document_ids"]).issubset(self.records))
            self.assertTrue(case["memory_user_id"])

    def test_fixture_covers_capstone_safety_behaviors(self) -> None:
        behaviors = {case["expected_behavior"] for case in self.evaluation["cases"]}
        self.assertIn("grounded_personalized", behaviors)
        self.assertIn("grounded_without_personalization", behaviors)
        self.assertIn("abstain_or_uncertainty", behaviors)
        self.assertIn("ignore_untrusted_instruction", behaviors)

    def test_fixture_covers_bounded_tool_behaviors(self) -> None:
        tool_cases = self.evaluation.get("tool_cases", [])
        self.assertGreaterEqual(len(tool_cases), 3)
        self.assertEqual(
            {case["check"] for case in tool_cases},
            {"typed_schema", "offline_fallback", "source_separation"},
        )

    def test_fixture_covers_before_and_after_reranking(self) -> None:
        reranking_cases = self.evaluation.get("reranking_cases", [])
        self.assertGreaterEqual(len(reranking_cases), 1)
        for case in reranking_cases:
            self.assertEqual(len(case["candidate_document_ids"]), len(case["vector_distances"]))
            self.assertIn(case["expected_document_id"], case["candidate_document_ids"])


if __name__ == "__main__":
    unittest.main()
