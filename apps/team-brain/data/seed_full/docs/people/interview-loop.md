# Interview loop

Owner: Henry (People). Standard loop for engineering; sales/marketing/
finance loops are shorter (skip the system design round below).

## Stages

1. **Recruiter screen** (30 min) — role fit, comp range, timeline.
2. **Hiring manager screen** (45 min) — background, motivation, a couple
   of technical judgment questions.
3. **Technical screen** (60 min) — a small, realistic coding exercise
   close to the actual work (for engineering: something adjacent to
   invoicing-api or reconciliation logic, never a pure algorithms puzzle).
4. **Onsite loop** (half day, 4 interviews):
   - System design (for senior+ roles) — often uses ledger-core's
     event-sourced model as a discussion prompt, see
     `engineering/adr-0007-event-sourced-ledger.md` for the internal
     version interviewers should NOT read verbatim to candidates.
   - Coding/pairing
   - Cross-functional collaboration (with someone from a team the role
     works closely with — e.g. an ops interviewer for a role touching
     `ops/infra-capacity-planning.md`-type work)
   - Values/culture, with Henry or a values-trained interviewer

## Debrief

Same day if possible, next day at latest. Each interviewer submits a
written scorecard before the debrief starts, so group discussion doesn't
anchor on whoever speaks first.

## Offer

Hiring manager + Henry align on level and comp band before an offer goes
out; anything outside the standard band needs Brian's sign-off, same
escalation pattern as an out-of-band discount or payment term
(`sales/deal-desk-policy.md`, `finance/vendor-payment-terms.md`).

New hires start the technical onboarding in
`engineering/onboarding-guide.md` on day one.
