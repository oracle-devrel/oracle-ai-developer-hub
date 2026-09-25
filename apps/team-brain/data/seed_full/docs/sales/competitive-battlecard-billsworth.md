# Competitive battlecard: Billsworth

Billsworth shows up mostly in deals sourced from developer-heavy buying
committees (they lead with API-first messaging).

## Where we win

- Billsworth's API is genuinely good, but their invoicing UI is
  developer-facing only — finance teams end up needing a second tool for
  anything visual. We're the only one of the two with a finance-usable UI
  and an API, per the architecture in
  `engineering/architecture-overview.md`.
- Support model: Billsworth is self-serve-first with paid support tiers;
  every Acme Ledger plan includes support, which matters to buyers who got
  burned by a surprise support bill elsewhere.

## Where we lose

- Pure API-first buyers (usually the smallest accounts we see) sometimes
  prefer Billsworth's lighter integration footprint if they have no
  finance stakeholder in the room at all. Not worth chasing with a
  discount — see `sales/discount-matrix.md`, these accounts rarely hit
  the contract sizes where a bigger discount would matter anyway.

## Talk track

Ask early who on the buying committee will actually use the product
day-to-day. If it's finance as well as engineering, the second-tool
problem with Billsworth becomes the deciding factor. If it's engineering
only, this may not be a deal worth heavily discounting to win — see
`sales/deal-desk-policy.md` on when a discount is warranted at all.

## Objection: "Billsworth's API is more flexible"

Agree, then pivot: flexible for whom. Their reconciliation still runs
through a mutable balance model per public docs, which means the same
class of drift issue our ADR-0007 solved for us. Don't over-technical this
in a sales call; the plain version is "explainable balances, always."
