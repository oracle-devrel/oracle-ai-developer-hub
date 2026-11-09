from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_paris_dataset import DatasetValidationError, build, verify_release


class ParisDatasetBuildTest(unittest.TestCase):
    def test_committed_release_matches_reviewed_fixture(self) -> None:
        result = verify_release(Path("data/manifest.yaml"))
        self.assertEqual(result["record_count"], 40)
        self.assertEqual(result["release_path"], "data/releases/paris_dataset_v2026.1.jsonl")

    def test_fixture_build_is_deterministic_and_reports_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = build(Path("data/manifest.yaml"), root / "dataset.jsonl", root / "report.json")
            self.assertEqual(report["record_count"], 40)
            self.assertTrue(report["dataset_hash"].startswith("sha256:"))
            self.assertEqual(report["failed_sources"], [])
            self.assertEqual(
                json.loads((root / "report.json").read_text())["corpus_version"], "2026.1"
            )

    def test_rejects_unreviewed_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "bad.jsonl"
            document = json.loads(
                Path("data/fixtures/paris_dataset_v2026.1.jsonl").read_text().splitlines()[0]
            )
            document["source_url"] = "https://unreviewed.example.invalid/"
            fixture.write_text(json.dumps(document) + "\n")
            manifest = root / "manifest.yaml"
            manifest.write_text(
                "corpus_name: Paris Dataset\ncorpus_version: '2026.1'\nfixture_path: "
                + str(fixture)
                + "\nsources: []\n"
            )
            with self.assertRaises(DatasetValidationError):
                build(manifest, root / "output.jsonl", root / "report.json")


if __name__ == "__main__":
    unittest.main()
