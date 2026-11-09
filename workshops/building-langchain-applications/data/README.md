# Paris Dataset data contract

The Paris Dataset is a governed corpus, not a scrape of public web pages.
Every record in the fixture has a stable ID, source URL, publisher, retrieval
date, explicit reuse basis, licence URL, and content hash. The reviewed source
manifest pins the fixture checksum separately.

## Fixture scope

`releases/paris_dataset_v2026.1.jsonl` is the committed, offline-safe 40-record dataset
that the tutorial uses. The separate `fixtures/` input is retained only for
maintainer validation of the release. Its short teaching summaries are
bounded: they do not assert live opening hours, availability, fares, service
status, or detailed venue facts. It is intentionally not yet the 40–80 record
release corpus described in the project plan.

The initial sources are Paris Data and Île-de-France Mobilités open-data
catalogues, plus individual Wikipedia references recorded with their CC BY-SA
4.0 reuse basis. Their reuse bases are explicit rather than treating a publicly
visible page as automatically reusable.
Attribution text is in `manifest.yaml`; future source additions must retain
the relevant attribution and licence terms.

## Build

Learners and CI verify the prebuilt release from the repository root:

```bash
venv/bin/python scripts/build_paris_dataset.py --verify-release
```

Maintainers can regenerate a candidate under `build/` for review:

```bash
venv/bin/python scripts/build_paris_dataset.py
```

Neither path crawls the web. The learner path reads no external source and does
not write corpus data. A changed fixture hash,
unknown source, licence mismatch, schema-field mismatch, duplicate ID, or
invalid record content hash stops the build with an explicit error.

## Adding material

Before adding a record, add or review its source in `manifest.yaml`, verify
that the intended reuse is permitted, write the required metadata, calculate
the record hash, and update the fixture checksum. If reuse is unclear, exclude
the material or retain only a link with a documented lawful basis. Do not add
copied pages simply because they are accessible on the web.
