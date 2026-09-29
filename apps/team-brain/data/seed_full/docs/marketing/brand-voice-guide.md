# Brand voice guide

Acme Ledger talks like the finance lead we're selling to: direct, numbers
first, no hype. This applies to landing pages, emails, and customer-facing
incident status updates (see `ops/incident-response-process.md` — status
page copy during an incident follows the same rules, doubly important
under pressure).

## Do

- Lead with the number: "cut close time by 4 days," not "revolutionize
  your close process."
- Say what changed and why, in that order.
- Use "we" for the company, never "our team of experts."

## Don't

- No error codes, stack traces, or internal service names
  (`billing-service`, `ledger-core`) in customer-visible copy — customers
  don't know or care what `ERR_BILLING_407` means, they care whether their
  invoices are generating.
- No "circle back," no "synergy," no "leverage" as a verb.
- Don't promise a fix time in a status update unless engineering has
  confirmed it. "We're investigating" beats a wrong ETA every time — the
  Q1 status page incident where we promised a 30-minute fix and took two
  hours cost us three logo-risk conversations.

## Review

Any external copy touching pricing or discounting gets a pass from Brian
before it ships — see `sales/discount-matrix.md` for the numbers that
must never appear in public marketing copy (the multi-year 30% ceiling is
sales-only, never advertised, so every prospect negotiates individually).

## Voice examples

Good: "Acme Ledger reconciles Stripe and your ledger automatically —
most customers stop doing it by hand within a week."

Bad: "Unlock next-generation revenue intelligence with our
enterprise-grade reconciliation engine."
