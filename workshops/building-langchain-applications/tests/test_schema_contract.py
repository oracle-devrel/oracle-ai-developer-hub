from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.build_paris_dataset import DatasetValidationError, load_manifest, validate_documents


class DatasetSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(Path("data/manifest.yaml"))
        cls.document = json.loads(Path("data/fixtures/paris_dataset_v2026.1.jsonl").read_text(encoding="utf-8").splitlines()[0])
        cls.sources = cls.manifest["sources"]

    def assert_rejected(self, document: dict[str, object]) -> None:
        with self.assertRaises(DatasetValidationError):
            validate_documents([document], self.sources)

    def test_reviewed_record_satisfies_schema_and_manifest(self) -> None:
        validate_documents([copy.deepcopy(self.document)], self.sources)

    def test_rejects_invalid_document_id_pattern(self) -> None:
        document = copy.deepcopy(self.document)
        document["document_id"] = "Invalid ID"
        self.assert_rejected(document)

    def test_rejects_invalid_retrieval_date(self) -> None:
        document = copy.deepcopy(self.document)
        document["retrieved_at"] = "15-Aug-2026"
        self.assert_rejected(document)

    def test_rejects_invalid_uri(self) -> None:
        document = copy.deepcopy(self.document)
        document["license_url"] = "not a URI"
        self.assert_rejected(document)

    def test_rejects_missing_and_extra_fields(self) -> None:
        missing = copy.deepcopy(self.document)
        del missing["title"]
        self.assert_rejected(missing)

        extra = copy.deepcopy(self.document)
        extra["unexpected"] = "not part of the contract"
        self.assert_rejected(extra)

    def test_rejects_invalid_enums(self) -> None:
        document = copy.deepcopy(self.document)
        document["topic"] = "unknown"
        self.assert_rejected(document)

        document = copy.deepcopy(self.document)
        document["license_basis"] = "unknown"
        self.assert_rejected(document)


if __name__ == "__main__":
    unittest.main()
