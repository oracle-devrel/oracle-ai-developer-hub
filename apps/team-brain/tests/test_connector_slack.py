"""Slack connector: thread → Document, and private channel → restricted+acl.

Unchanged by the Oracle port — this connector has no database dependency; it
only needs conftest's offline LLM env for enrich_thread() (a no-op offline).
"""

from __future__ import annotations

import json
import os

import pytest

from team_brain.connectors.slack import SlackConnector

pytestmark = pytest.mark.requires_oracle


def test_export_threads_become_documents(slack_export: str) -> None:
    docs = list(SlackConnector(export_path=slack_export).fetch())
    by_id = {d.external_id: d for d in docs}
    # two public engineering threads + one private security thread
    assert len(docs) == 3

    eng = by_id["C_ENG:1717000000.000100"]
    assert eng.visibility == "public"
    assert eng.acl == []
    assert eng.author == "bob"
    assert "onnxruntime" in eng.body
    assert eng.metadata["channel"] == "engineering"


def test_private_channel_is_restricted_with_member_acl(slack_export: str) -> None:
    docs = list(SlackConnector(export_path=slack_export).fetch())
    private = next(d for d in docs if d.metadata["channel"] == "security-incidents")
    assert private.visibility == "restricted"
    assert private.acl == ["bob"]  # explicit operator mapping, independent of display name
    assert "hunter2" in private.body  # secret is IN the body...
    # ...which is exactly why the permission filter (tested elsewhere) matters.


def test_missing_export_raises() -> None:
    with pytest.raises(FileNotFoundError):
        list(SlackConnector(export_path="nope.json").fetch())


@pytest.mark.parametrize("mapped", [False, True])
def test_duplicate_slack_names_do_not_grant_private_access(db, tmp_path, mapped):
    from team_brain.access import AccessControl, Identity

    export = {
        "users": {"U_MEMBER": "alex", "U_OUTSIDER": "alex"},
        "channels": [
            {
                "id": "C_PRIVATE",
                "is_private": True,
                "members": ["U_MEMBER"],
                "threads": [
                    {
                        "thread_ts": "1717000000",
                        "messages": [{"user": "U_MEMBER", "text": "private secret"}],
                    }
                ],
            }
        ],
    }
    if mapped:
        export["principal_map"] = {"U_MEMBER": "member", "U_OUTSIDER": "alex"}
    path = tmp_path / "slack.json"
    path.write_text(json.dumps(export), encoding="utf-8")
    doc = next(iter(SlackConnector(str(path)).fetch()))
    assert doc.author == "alex"
    member = "member" if mapped else "U_MEMBER"
    assert doc.acl == [member]
    db.upsert_document(doc)
    db.commit()
    ac = AccessControl()
    try:
        for principal in (member, "alex", "U_OUTSIDER"):
            ac.upsert_principal(principal, "alex", [])
            ac.add_token(f"test-slack-{principal}", principal, label="collision regression")
        ac.commit()
    finally:
        ac.close()
    for principal in (member, "alex", "U_OUTSIDER"):
        db.set_identity(Identity.token(f"test-slack-{principal}"))
        assert (db.get_document("slack::C_PRIVATE:1717000000") is not None) == (principal == member)


def test_cli_identity_map_overrides_export_names(tmp_path, slack_export):
    from team_brain.connectors import build_connector

    path = tmp_path / "identities.json"
    path.write_text(json.dumps({"U_BOB": "mapped-member"}), encoding="utf-8")
    connector = build_connector("slack", ["--identity-map", str(path), "--export", slack_export])
    private = next(d for d in connector.fetch() if d.visibility == "restricted")
    assert private.acl == ["mapped-member"]


@pytest.mark.parametrize("mapping", [{"U_MEMBER": ""}, {"U_MEMBER": None}, ["alex"]])
def test_invalid_identity_map_is_rejected(mapping):
    with pytest.raises(ValueError, match="principal_map"):
        SlackConnector(principal_map=mapping)


def test_live_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("team_brain.connectors.slack.SLACK_BOT_TOKEN", "")
    with pytest.raises(ValueError):
        list(SlackConnector().fetch())


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("TEAMBRAIN_LIVE"), reason="live: set TEAMBRAIN_LIVE=1")
def test_slack_live_smoke() -> None:
    docs = list(SlackConnector().fetch())
    assert isinstance(docs, list)
