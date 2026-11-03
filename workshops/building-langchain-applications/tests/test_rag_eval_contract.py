from __future__ import annotations

import json
import unittest
from pathlib import Path


class RagEvaluationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evaluation = json.loads(Path("data/evals/rag_eval_v2026.1.json").read_text(encoding="utf-8"))
        cls.records = {
            json.loads(line)["document_id"]
            for line in Path("data/releases/paris_dataset_v2026.1.jsonl").read_text(encoding="utf-8").splitlines()
        }

    def test_fixture_is_versioned_and_references_only_release_records(self) -> None:
        self.assertEqual(self.evaluation["corpus_name"], "Paris Dataset")
        self.assertEqual(self.evaluation["corpus_version"], "2026.1")
        self.assertGreaterEqual(len(self.evaluation["cases"]), 4)
        for case in self.evaluation["cases"]:
            self.assertTrue(case["case_id"])
            self.assertIn(case["expected_behavior"], {"grounded", "abstain", "abstain_or_uncertainty"})
            self.assertTrue(set(case["expected_document_ids"]).issubset(self.records))

    def test_fixture_contains_grounding_and_abstention_cases(self) -> None:
        behaviors = {case["expected_behavior"] for case in self.evaluation["cases"]}
        self.assertIn("grounded", behaviors)
        self.assertIn("abstain", behaviors)
        self.assertIn("abstain_or_uncertainty", behaviors)


if __name__ == "__main__":
    unittest.main()
