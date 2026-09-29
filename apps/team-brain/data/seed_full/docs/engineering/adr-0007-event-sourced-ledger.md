# ADR-0007: Move ledger-core to event sourcing

**Status:** Accepted, 2026-03-11. **Author:** Carla.

## Context

The original ledger-core stored a single mutable `balances` row per account.
Two 2025 incidents (a double-refund and a race condition between a charge
and a plan downgrade) both traced back to the same root cause: nothing
recorded what changed a balance, only its current value, so reconciliation
couldn't tell WHY Stripe and our number disagreed.

## Decision

Ledger-core now stores an append-only `ledger_events` stream (charge,
refund, credit, adjustment); balances are a projection computed from the
stream, rebuildable at any time. This is the same "append vs. replace"
distinction the on-call rotation doc and the reconciliation-worker rely on.

## Consequences

- Every balance is auditable back to the event that produced it — this is
  what let us close the July 14 billing outage postmortem
  (`engineering/postmortem-2026-07-14-billing-outage.md`) in under a day.
- Ledger-core migrations now require a maintenance window (rebuilding
  projections at scale takes 20-40 minutes), unlike billing-service's
  zero-downtime blue-green deploys. Scheduled Sundays 02:00-04:00 CT.
- Reconciliation-worker's nightly diff job got simpler: it replays events
  since the last checkpoint instead of diffing two live tables.

## Alternatives considered

Keeping mutable balances with a separate audit log was rejected — it's the
same information duplicated in two places that can drift, which was the
exact failure mode we were trying to eliminate.
