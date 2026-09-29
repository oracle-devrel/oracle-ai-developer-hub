"""Unit tests for the Document contract. Unchanged by the Oracle port."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from team_brain.schema import Document


def _doc(**kw: object) -> Document:
    base: dict[str, object] = {
        "source": "md",
        "external_id": "x",
        "title": "t",
        "body": "b",
        "created_at": datetime.now(UTC),
    }
    base.update(kw)
    return Document(**base)  # type: ignore[arg-type]


def test_content_hash_is_stable() -> None:
    d1 = _doc()
    d2 = _doc()
    assert d1.content_hash() == d2.content_hash()
    assert _doc(body="different").content_hash() != d1.content_hash()


def test_requires_source_and_external_id() -> None:
    with pytest.raises(ValueError):
        _doc(source="")
    with pytest.raises(ValueError):
        _doc(external_id="")


def test_visibility_must_be_valid() -> None:
    with pytest.raises(ValueError):
        _doc(visibility="secret")
    assert _doc(visibility="restricted", acl=["bob"]).visibility == "restricted"


def test_created_at_must_be_tz_aware() -> None:
    with pytest.raises(ValueError):
        _doc(created_at=datetime(2026, 1, 1))  # naive


def test_fail_closed_when_restricted_without_acl() -> None:
    assert _doc(visibility="restricted", acl=[]).fail_closed() is True
    assert _doc(visibility="restricted", acl=["bob"]).fail_closed() is False
    assert _doc(visibility="public").fail_closed() is False
