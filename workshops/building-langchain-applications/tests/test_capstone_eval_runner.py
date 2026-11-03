from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_capstone_eval import run_evaluation


class CapstoneEvaluationRunnerTest(unittest.TestCase):
    def test_offline_runner_scores_policy_cases_but_marks_live_gate_unrun(self) -> None:
        report = run_evaluation()

        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["score_percent"], 85)
        self.assertEqual(report["case_score_percent"], 100.0)
        self.assertEqual(report["passed_cases"], report["total_cases"])
        self.assertEqual(report["hard_gates"]["memory_lifecycle_live"]["status"], "not_run")
        self.assertTrue(all(case["passed"] for case in report["cases"]))
        injection_case = next(case for case in report["cases"] if case["case_id"] == "untrusted-corpus-instruction")
        self.assertEqual(injection_case["personalization_used"], [])

    def test_report_shape_is_json_serializable(self) -> None:
        report = run_evaluation()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capstone-report.json"
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["evaluation"], "capstone")
        self.assertIn("hard_gates", loaded)
        self.assertIn("cases", loaded)

    def test_live_mode_requires_both_integration_and_injection_gates(self) -> None:
        with (
            patch(
                "scripts.run_capstone_eval._run_live_integration",
                return_value={"status": "passed", "detail": "integration ok"},
            ),
            patch(
                "scripts.run_capstone_eval._run_live_injection_probe",
                return_value={"status": "passed", "detail": "injection ok"},
            ),
            patch(
                "scripts.run_capstone_eval._run_live_weather_tool_probe",
                return_value={"status": "passed", "detail": "tool ok"},
            ),
        ):
            report = run_evaluation(run_live=True)

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["hard_gates"]["memory_lifecycle_live"]["status"], "passed")
        self.assertEqual(report["hard_gates"]["injection_resistance"]["status"], "passed")
        self.assertEqual(report["hard_gates"]["tool_agent_live"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
