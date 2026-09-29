# Engineering onboarding guide

Welcome to Acme Ledger engineering. This is the technical half of onboarding;
the HR half (paperwork, benefits, interview loop for future hires) is in
`people/new-hire-checklist.md`.

## Week 1

- Day 1: laptop + GitHub/AWS/Oracle Cloud access provisioned by IT before
  your start date. Read `engineering/architecture-overview.md` end to end.
- Day 2: shadow the on-call handover (Mondays 10:00 CT) even if you're not
  on the rotation yet — see `ops/oncall-rotation.md`.
- Day 3-4: ship a small fix to `invoicing-api` (docs list "good first
  issue" tickets) and go through the full `deploy-billing`-style pipeline
  in staging so the deploy runbook (`engineering/deploy-runbook.md`) isn't
  abstract.
- Day 5: read ADR-0007 (`engineering/adr-0007-event-sourced-ledger.md`) and
  the July 14 postmortem so you understand why ledger-core migrations need
  a maintenance window.

## Access checklist

- `#engineering` and `#ops-team` Slack (company-wide access; ops requires
  the ops group grant if you're touching infra)
- Staging database credentials (never prod — prod access is requested
  separately and logged)
- PagerDuty, added to the secondary rotation after 30 days, primary after
  90

## Who to ask

- Ledger-core / event schema: Carla
- Reconciliation-worker / drift alerts: Dave
- Infra / autoscaling / secrets: Jeff (ops)
- On-call process questions: Alice

New engineers are not on the on-call rotation until they've completed the
week-1 checklist above and shadowed at least one live handover.
