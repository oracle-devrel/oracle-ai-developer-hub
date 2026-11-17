# Incident response process

Severity 1 (customer-facing outage) opens an incident channel immediately
and pings the incident commander — whoever is primary on-call per
`ops/oncall-rotation.md`, unless a more senior engineer is already engaged,
in which case they take the IC role explicitly (say so in the channel, no
implicit handoffs).

## Severity levels

- **Sev-1**: customer-facing outage or data integrity risk (e.g. invoices
  not generating, balances drifting). Page immediately, IC required.
- **Sev-2**: degraded but not down (elevated latency, a single account
  affected). Fix during business hours, no page required overnight.
- **Sev-3**: internal-only or cosmetic. Ticket, no incident channel.

## During the incident

1. IC posts a timeline update every 15 minutes, even if the update is
   "still investigating."
2. Any credential that touched the incident path gets rotated as part of
   the fix, not as a follow-up — this became a hard rule after an earlier
   incident where a leaked staging database password reached prod and
   sat un-rotated for two days before anyone noticed.
3. Customer-facing status page updated by whoever is on marketing on-call
   (see `marketing/brand-voice-guide.md` for the tone rules on status
   updates — no jargon, no error codes in customer-visible text).

## After the incident

Postmortem due within 48 hours, blameless, filed next to
`engineering/postmortem-2026-07-14-billing-outage.md`. Every postmortem
needs at least one action item with an owner and a date, not just a
description of what happened.

Anything discussed in the `#security-incidents` channel (private,
ops-domain) that involves an active exploit or unrotated credential stays
in that channel until the credential is rotated — do not paraphrase details
into a public postmortem before the fix ships.
