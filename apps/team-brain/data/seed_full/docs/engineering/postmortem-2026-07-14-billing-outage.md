# Postmortem: billing service outage, 2026-07-14

**Severity:** 1 (customer-facing). **Incident commander:** Alice.
**Duration:** 47 minutes (14:02-14:49 CT).

## Summary

Invoice generation failed for roughly 8% of accounts. Root cause: a
`deploy-billing` release rotated the Stripe webhook secret, but the new
secret hadn't propagated to the `billing-prod` secret group in the
request-serving pool yet, so webhook verification failed with
`ERR_BILLING_407` for any account on that pool until the propagation
finished. This is the same secret group referenced in
`engineering/deploy-runbook.md`.

## Timeline

- 14:02 — error rate alert fires, on-call (Alice) acknowledges within 3
  minutes.
- 14:06 — incident channel opened per `ops/incident-response-process.md`;
  Alice as incident commander.
- 14:20 — root cause identified: stale webhook secret.
- 14:35 — `scripts/sync_billing_secrets.sh` re-run manually to force
  propagation.
- 14:49 — error rate back to baseline, incident closed.

## A separate, unrelated public note

Earlier this year a related-but-distinct incident is worth recording here
for the team's institutional memory: an API outage was traced back to a
leaked staging database password used against prod. All credentials were
rotated afterward and an IP allowlist was added for the staging-to-prod
path. That fix is why `ops/incident-response-process.md` now requires a
credential rotation checklist item on every Sev-1.

## Follow-ups

1. `deploy-billing` now waits for secret propagation to be confirmed in all
   pools before completing (owner: Alice, done 2026-07-18).
2. Reconciliation-worker's drift alert threshold tightened from $5 to $1 so
   this class of issue pages faster next time (owner: Dave).
3. Postmortem published within 48 hours per the on-call rotation policy.
