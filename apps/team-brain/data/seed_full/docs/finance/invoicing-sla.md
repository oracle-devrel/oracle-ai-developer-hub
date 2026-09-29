# Internal invoicing SLA

Owner: Bob (Finance), jointly with Alice on the engineering side since
invoicing-api generates the underlying documents (see
`engineering/architecture-overview.md`).

## Targets

- Monthly statements generate by the 1st business day of the month, 06:00
  CT, via the batch node pool (`ops/infra-capacity-planning.md`).
- Invoice corrections (a customer disputes a line item) resolved within 3
  business days of the ticket being filed.
- Failed invoice generation (any `ERR_BILLING_*` class error) pages
  on-call per `ops/oncall-rotation.md` if it affects more than 1% of
  accounts; single-account failures are a next-business-day fix.

## What counts as a miss

A miss is any statement generating more than 4 hours past the 06:00 CT
target, or any correction unresolved past 3 business days without a
customer-facing update. Misses get logged the same way an incident does
(`ops/incident-response-process.md`), even if no customer noticed, because
the pattern across quiet misses is often the leading indicator of a real
outage.

## History

Q2 2026 had one miss: the batch pool hit node pressure before the
autoscaler change described in `ops/autoscaler-decision-log.md`, delaying
statements by 5 hours for roughly 200 accounts. Zero misses since that
change shipped.

## Reporting

Bob reviews the SLA monthly with Brian; any miss gets a one-line root
cause even if it's "known infra issue, already fixed" so the trend is
visible over time rather than each miss looking isolated.
