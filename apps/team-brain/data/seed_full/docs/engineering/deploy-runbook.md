# Deploying the billing service

Acme Ledger's billing service deploys to production via the `deploy-billing`
GitHub Action. It runs the migration step first (`alembic upgrade head`),
then a blue-green cutover: the new revision takes traffic only after its
health check passes on port 8080 for 60 consecutive seconds. If the migration
fails, the workflow halts before any traffic shifts, so a bad migration never
takes down production.

Rollback: re-run the `deploy-billing` action pinned to the previous release
tag (e.g. `v2026.07.2` instead of `v2026.07.3`). The blue-green cutover means
rollback is also zero-downtime — traffic just flips back to the still-warm
previous release. The Stripe webhook secret and the ledger-core database
password both live in the `billing-prod` secret group, not in the repo; see
`ops/infra-capacity-planning.md` for how that secret group is provisioned.

Invoicing-api and reconciliation-worker deploy the same way, via
`deploy-invoicing` and `deploy-reconciliation`, sharing the same GitHub
Actions template. Ledger-core (the event-sourced core described in
`engineering/adr-0007-event-sourced-ledger.md`) deploys separately because
schema migrations there require a maintenance window — see that ADR for why.

On-call owner: Alice. Escalation and handover live in
`ops/oncall-rotation.md`. If a deploy causes a customer-facing incident,
follow `ops/incident-response-process.md` and open a channel immediately;
don't wait for the postmortem to start investigating.

Common deploy failures: `ERR_BILLING_407` means the Stripe webhook signature
check failed (usually a stale secret after rotation — re-run
`scripts/sync_billing_secrets.sh`). `ORA-12154` during migration means the
ledger-core database's TNS alias is wrong in that environment's connect
string; check `ops/infra-capacity-planning.md` for the current DSNs per
environment.
