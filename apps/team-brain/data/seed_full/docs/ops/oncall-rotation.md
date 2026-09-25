# On-call rotation and escalation

The on-call rotation runs weekly, handed over every Monday at 10:00 CT.
Primary on-call acknowledges pages within 5 minutes; if unacked after 10
minutes it escalates to the secondary, then to the engineering lead after
another 10 minutes.

Severity 1 (customer-facing outage) also opens an incident channel and
pings the incident commander, per `ops/incident-response-process.md`.
Postmortems are due within 48 hours and are blameless — see
`engineering/postmortem-2026-07-14-billing-outage.md` for the current
template and an example.

The escalation policy lives in PagerDuty under "Platform - Prod". New
engineers join the secondary rotation after 30 days and primary after 90,
per `engineering/onboarding-guide.md`.

## Current rotation (Q3 2026)

| Week of    | Primary | Secondary |
| ---------- | ------- | --------- |
| 2026-09-01 | Alice   | Dave      |
| 2026-09-08 | Dave    | Carla     |
| 2026-09-15 | Jeff    | Alice     |
| 2026-09-22 | Carla   | Jeff      |

Jeff covers infra-only pages (autoscaler, cluster capacity — see
`ops/infra-capacity-planning.md`); billing-service and ledger-core pages
always go to an engineering primary regardless of whose infra week it is.

If you're unsure whether something is a page-worthy Sev-1 versus a
next-business-day bug, default to paging — the cost of a false page is a
5-minute Slack thread; the cost of a missed Sev-1 is measured in customer
invoices that silently fail to generate.
