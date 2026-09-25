# Infra capacity planning

Acme Ledger runs on the `acme-prod-use1` Kubernetes cluster (see
`engineering/architecture-overview.md`). Two node pools:

- **request-serving pool**: fixed at 8 nodes, fronts billing-service,
  invoicing-api, and reconciliation-worker's API. Scales manually; a
  capacity review happens each quarter tied to signed-contract growth (see
  `finance/revenue-recognition-notes.md` for the contract pipeline this is
  based on).
- **batch node pool**: autoscales for nightly reconciliation and monthly
  statement generation. Current range is 6 to 10 nodes with a 15-minute
  scale-down cooldown — see `ops/autoscaler-decision-log.md` for why that
  changed from a flat 6-node pool.

## Secrets

The `billing-prod` secret group holds the Stripe webhook secret and the
ledger-core database password, synced to both node pools via
`scripts/sync_billing_secrets.sh`. Rotation is quarterly, or immediately
after any incident that touched a credential (see
`ops/incident-response-process.md`).

## Database connectivity

Ledger-core's database connect strings are environment-specific TNS
aliases. A wrong or stale alias raises `ORA-12154` at connection time — the
July 2026 staging incident was exactly this: a TNS entry pointed at a
decommissioned host after a datacenter migration. Current aliases are
tracked in the `infra` repo's `tnsnames.ora`, not in this doc, so they
don't go stale here too.

## On the roadmap

Q4 2026: move the batch pool to spot instances for the non-time-critical
half of the monthly statement run, projected to cut batch compute cost
~35%. Jeff is scoping this; see the ops-team Slack channel for the current
state of that investigation.
