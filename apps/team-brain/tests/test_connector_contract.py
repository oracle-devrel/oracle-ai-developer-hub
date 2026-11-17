"""Every registered connector emits contract-valid Documents.

Parametrized over the registry, so any connector an attendee adds is
automatically held to the contract (given a way to build it offline).
Unchanged by the Oracle port — connectors know nothing about the database.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from team_brain.config import REPO_DIR
from team_brain.connectors import Connector, build_connector
from team_brain.schema import Document

# name -> args that build the connector deterministically & offline.
OFFLINE_BUILDS: dict[str, list[str]] = {
    "markdown": [str(REPO_DIR / "data" / "seed" / "docs")],
    "slack": ["--export", str(REPO_DIR / "data" / "seed" / "slack_export.json")],
}


@pytest.mark.parametrize("name", sorted(OFFLINE_BUILDS))
def test_connector_emits_valid_documents(name: str) -> None:
    connector: Connector = build_connector(name, OFFLINE_BUILDS[name])
    assert connector.source == name
    docs = list(connector.fetch())
    assert docs, f"{name} produced no documents"
    for d in docs:
        assert isinstance(d, Document)
        assert d.source == name
        assert d.external_id
        assert d.created_at.tzinfo is not None
        assert d.visibility in ("public", "restricted")
        if d.visibility == "restricted":
            assert isinstance(d.acl, list)


def test_registry_exposes_builder() -> None:
    from team_brain.connectors import registered

    assert "markdown" in registered()
    assert "slack" in registered()
    assert "github" in registered()
    assert isinstance(build_connector, Callable)  # type: ignore[arg-type]


def test_unknown_connector_raises() -> None:
    with pytest.raises(KeyError):
        build_connector("does-not-exist", [])
