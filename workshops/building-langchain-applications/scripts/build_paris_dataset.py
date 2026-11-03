"""Build and validate the versioned Paris Dataset fixture without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data/schema.json"


class DatasetValidationError(ValueError):
    """Raised when a source record or fixture violates the data contract."""


def canonical_document(document: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in document.items() if key != "content_hash"}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_hash(document: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_document(document)).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise DatasetValidationError("manifest must contain a sources list")
    if not isinstance(manifest.get("corpus_version"), str):
        raise DatasetValidationError("manifest must contain corpus_version")
    return manifest


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    if not isinstance(schema, dict):
        raise DatasetValidationError("dataset schema must be a JSON object")
    return schema


def load_fixture(path: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError as error:
                raise DatasetValidationError(f"invalid JSON at {path}:{line_number}") from error
            if not isinstance(document, dict):
                raise DatasetValidationError(f"record at {path}:{line_number} must be an object")
            documents.append(document)
    return documents


def validate_documents(documents: list[dict[str, Any]], sources: list[dict[str, Any]]) -> None:
    source_by_url = {source["source_url"]: source for source in sources}
    schema = load_schema()
    required_fields = set(schema.get("required", []))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    identifiers: set[str] = set()
    for document in documents:
        schema_errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
        if schema_errors:
            error = schema_errors[0]
            location = ".".join(str(part) for part in error.absolute_path) or "<document>"
            raise DatasetValidationError(
                f"{document.get('document_id', '<unknown>')}: schema validation failed at {location}: {error.message}"
            )
        missing = required_fields - document.keys()
        extra = document.keys() - required_fields
        if missing or extra:
            raise DatasetValidationError(f"{document.get('document_id', '<unknown>')}: missing={sorted(missing)} extra={sorted(extra)}")
        identifier = document["document_id"]
        if not isinstance(identifier, str) or identifier in identifiers:
            raise DatasetValidationError(f"duplicate or invalid document_id: {identifier!r}")
        identifiers.add(identifier)
        source = source_by_url.get(document["source_url"])
        if source is None:
            matching_prefixes = [
                candidate for candidate in sources
                if isinstance(candidate.get("source_url_prefix"), str)
                and document["source_url"].startswith(candidate["source_url_prefix"])
            ]
            source = max(matching_prefixes, key=lambda candidate: len(candidate["source_url_prefix"]), default=None)
        if source is None:
            raise DatasetValidationError(f"{identifier}: source_url is not reviewed in manifest")
        for key in ("source_publisher", "license_basis", "license_url", "retrieved_at"):
            if document[key] != source[key.replace("source_", "") if key.startswith("source_") else key]:
                raise DatasetValidationError(f"{identifier}: {key} does not match reviewed source")
        if document["content_hash"] != content_hash(document):
            raise DatasetValidationError(f"{identifier}: content_hash does not match content")


def canonical_dataset(documents: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n" for document in documents)


def build(manifest_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    fixture_path = ROOT / manifest["fixture_path"]
    fixture_hash = "sha256:" + hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    if manifest.get("fixture_sha256") != fixture_hash:
        raise DatasetValidationError("fixture_sha256 does not match the reviewed fixture")
    documents = sorted(load_fixture(fixture_path), key=lambda document: document["document_id"])
    validate_documents(documents, manifest["sources"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = canonical_dataset(documents)
    output_path.write_text(output, encoding="utf-8")
    report = {
        "corpus_name": manifest["corpus_name"],
        "corpus_version": manifest["corpus_version"],
        "record_count": len(documents),
        "dataset_hash": "sha256:" + hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "source_count": len(manifest["sources"]),
        "fixture_hash": fixture_hash,
        "failed_sources": [],
        "excluded_sources": [],
        "built_at": datetime.now(UTC).isoformat(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def verify_release(manifest_path: Path) -> dict[str, Any]:
    """Verify the committed release; this is the tutorial-safe data path."""
    manifest = load_manifest(manifest_path)
    fixture_path = ROOT / manifest["fixture_path"]
    fixture_hash = "sha256:" + hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    if manifest.get("fixture_sha256") != fixture_hash:
        raise DatasetValidationError("fixture_sha256 does not match the reviewed fixture")
    documents = sorted(load_fixture(fixture_path), key=lambda document: document["document_id"])
    validate_documents(documents, manifest["sources"])
    expected = canonical_dataset(documents).encode("utf-8")
    release_path = ROOT / manifest["release_path"]
    if not release_path.is_file():
        raise DatasetValidationError("committed release dataset is missing")
    actual = release_path.read_bytes()
    actual_hash = "sha256:" + hashlib.sha256(actual).hexdigest()
    if actual != expected or manifest.get("release_sha256") != actual_hash:
        raise DatasetValidationError("committed release differs from the reviewed canonical dataset")
    return {"record_count": len(documents), "dataset_hash": actual_hash, "release_path": str(release_path.relative_to(ROOT))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "build/paris_dataset.jsonl")
    parser.add_argument("--report", type=Path, default=ROOT / "build/paris_dataset_report.json")
    parser.add_argument("--verify-release", action="store_true", help="verify the committed release without writing data")
    args = parser.parse_args()
    if args.verify_release:
        result = verify_release(args.manifest)
        print(f"Verified {result['release_path']}: {result['record_count']} records with {result['dataset_hash']}")
        return
    report = build(args.manifest, args.output, args.report)
    print(f"Built {report['record_count']} records with {report['dataset_hash']}")


if __name__ == "__main__":
    main()
