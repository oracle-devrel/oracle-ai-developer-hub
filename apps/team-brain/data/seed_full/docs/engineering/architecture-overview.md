# Acme Ledger system architecture

Acme Ledger is a billing and invoicing platform for mid-market SaaS
companies: usage metering, invoice generation, dunning, and revenue
reporting. Four services make up the core:

- **billing-service** — owns subscription state and Stripe integration.
  Deploys via `deploy-billing`; see `engineering/deploy-runbook.md`.
- **invoicing-api** — public REST API partners call to fetch invoices and
  usage records. Rate-limited to 600 req/min per API key.
- **ledger-core** — the event-sourced source of truth for every balance
  change. Every credit, charge, and refund is an immutable event; balances
  are projections. See `engineering/adr-0007-event-sourced-ledger.md` for
  why we moved off a mutable-balance table in 2026.
- **reconciliation-worker** — nightly job that diffs ledger-core's
  projected balances against Stripe's records and pages ops if they drift
  by more than $1.00 across any account.

All four run in the `acme-prod-use1` Kubernetes cluster. The batch node
pool (nightly reconciliation, monthly statement generation) autoscales
separately from the request-serving pool — see
`ops/infra-capacity-planning.md` and `ops/autoscaler-decision-log.md` for
the current node counts and why they changed.

Feature flags gate every ledger-core-facing change; `ff-invoice-v2-templates`
is the current one in rollout (10% of accounts as of August). Flags are
managed centrally so a bad flag can be killed without a deploy.

New engineers: read this doc first, then `engineering/deploy-runbook.md`,
`ops/oncall-rotation.md`, and `engineering/onboarding-guide.md` in that
order. Questions about the reconciliation logic specifically go to Dave;
questions about ledger-core's event schema go to Carla.
