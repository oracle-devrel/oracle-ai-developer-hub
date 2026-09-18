# Write your own connector

A connector reads one source and yields `Document` rows in the shared schema.
That's the whole extension surface; everything downstream (embedding, hybrid
retrieval, permissions, the agent, MCP) works the moment your rows land.

**One connector per _source_, never per person.** A teammate is not a connector.
Identity is a property of the database session, and a row policy on the table
filters every read by it, so everyone queries the same brain and sees their own
permitted slice of it. See [PERSONAL_VS_TEAM.md](PERSONAL_VS_TEAM.md).

## Three steps

**1. Copy the template and implement `fetch()`.**

```bash
cp team_brain/connectors/TEMPLATE.py team_brain/connectors/notion.py
```

```python
from collections.abc import Iterable
from datetime import UTC, datetime
from team_brain.schema import Document

class NotionConnector:
    source = "notion"

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace

    def fetch(self) -> Iterable[Document]:
        for page in read_my_pages(self.workspace):      # your API calls
            yield Document(
                source=self.source,
                external_id=page.id,                    # stable → upsert key
                title=page.title,
                body=page.text,
                created_at=page.updated_at.astimezone(UTC),   # tz-aware!
                url=page.url,
                author=page.author,
                # For private content:
                # visibility="restricted", acl=["alice", "bob"],
            )
```

**2. Register a builder** in `team_brain/connectors/__init__.py`:

```python
def _build_notion(args: list[str]) -> Connector:
    from team_brain.connectors.notion import NotionConnector
    return NotionConnector(args[0])

register("notion", _build_notion)
```

**3. Ingest.**

```bash
uv run team-brain ingest notion my-workspace
uv run team-brain ask "what did we decide about pricing?" --user alice
```

## The contract (what `fetch()` must guarantee)

| Field                | Rule                                                                                                                                                                                                                                                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `source`             | matches your connector's `source`                                                                                                                                                                                                                                                                                                                            |
| `external_id`        | **stable** within the source, re-ingesting the same item updates in place, and anything you stop emitting gets tombstoned                                                                                                                                                                                                                                    |
| `created_at`         | timezone-aware (use `datetime.now(UTC)` if the source has no date)                                                                                                                                                                                                                                                                                           |
| `visibility` / `acl` | `"public"` for everyone; `"restricted"` + `acl=[members]` for private content. Restricted + empty `acl` = visible to nobody (fail-closed)                                                                                                                                                                                                                    |
| `domains`            | group-based access labels (e.g. `["ops"]`, `["ops","marketing"]`). Empty = company-wide. A caller sees a labeled doc only if their groups grant one of these domains. Stamp it from the source (a channel, a repo, a `--domain` arg), never from a person. Enforced at query time; see [PERSONAL_VS_TEAM.md](PERSONAL_VS_TEAM.md) and `team_brain/access.py` |
| `metadata`           | free-form; set `{"kind": "code"}` to make items show up in `search_code`                                                                                                                                                                                                                                                                                     |

`fetch()` returns a **full snapshot** of the current source state. Ingestion
upserts everything you yield and tombstones anything for your `source` that you
no longer yield, so deletes and now-private items drop out automatically.

## Enrichment (optional but recommended for chatty sources)

If your source is noisy (chat, comments), distill before embedding; see how
`team_brain/connectors/slack.py` calls `enrich_thread()` and stores the result
in `metadata["_enriched"]`. The ingest path embeds the distilled text when
present and falls back to `title + body` otherwise.

## Test it

The parametrized contract test (`tests/test_connector_contract.py`) automatically
holds every registered connector to the contract; add an offline build entry and
you get coverage for free.
