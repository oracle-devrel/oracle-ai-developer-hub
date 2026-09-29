# Decision log: batch autoscaler max

**Date:** 2026-08-11. **Owner:** Jeff.

## Problem

The batch node pool kept hitting node pressure during nightly
reconciliation reindex, occasionally pushing the job past its 90-minute
SLA and delaying the next morning's statement generation.

## Decision

Raised the ops batch node pool autoscaler max from 6 to 10 nodes and set a
scale-down cooldown of 15 minutes (previously the pool scaled down
immediately after load dropped, then thrashed back up 20 minutes later
when the next batch step started). Reindex now finishes under an hour.

This is the same node pool documented in
`ops/infra-capacity-planning.md`; that doc has the current authoritative
range, this log is the "why," kept so future-Jeff (or whoever inherits
this) doesn't re-litigate the same node-pressure investigation.

## Follow-up considered but not done

Splitting reconciliation and statement generation into separate pools was
considered and rejected for now — the two jobs never overlap in practice,
so a shared pool with a wider autoscale range was simpler than running two
smaller pools that would each need their own floor.

## Cost impact

Peak batch spend rose about 18% (more nodes at peak), but the SLA breach
that used to cost an engineer a morning of manual intervention roughly
once a month is gone. Revisit if the batch job's runtime profile changes
significantly, e.g. if ledger-core event volume triples.
