# Competitive battlecard: Ledgerly

Ledgerly is our most common competitive mention in mid-market deals,
especially companies already using a spreadsheet-heavy close process.

## Where we win

- Implementation speed: our median time-to-first-invoice is 9 days versus
  Ledgerly's reported 6-8 weeks, because our onboarding team maps existing
  Stripe data directly instead of requiring a manual chart-of-accounts
  rebuild.
- Reconciliation: our ledger-core event-sourced model (see
  `engineering/adr-0007-event-sourced-ledger.md` for the internal
  rationale — don't send this doc to prospects, just use the plain-English
  version) means every balance is explainable; Ledgerly's support forum has
  repeated threads about unexplained balance drift.

## Where we lose

- Ledgerly has native multi-entity consolidation; we don't yet (roadmap
  item, no committed date — don't promise one).
- Ledgerly's list price is roughly 15% below ours at the same tier, so
  price-sensitive prospects need the ROI story (time saved, not just
  cost), not a discount race — see `sales/discount-matrix.md` for how far
  we can actually move on price before it stops being profitable.

## Talk track

Lead with implementation speed and reconciliation confidence, not price.
If price comes up first, ask what their close process costs them in
person-hours today — most prospects haven't quantified it and the answer
usually favors us once time is priced in.

## Objection: "Ledgerly has been around longer"

True, and irrelevant to whether their reconciliation model produces
explainable balances. Offer a reference call with a customer who migrated
from Ledgerly (ask deal desk for the current reference list).
