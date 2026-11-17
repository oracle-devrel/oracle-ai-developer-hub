# Launch checklist: Q3 webinar campaign

Owner: Julia. Target: mid-market SaaS finance leaders evaluating a
billing platform switch.

## Pre-launch (T-2 weeks)

- [ ] Landing page copy reviewed against `marketing/brand-voice-guide.md`
- [ ] UTM scheme finalized and shared with sales (see below — sales uses
      the same scheme to attribute inbound to the webinar in the CRM)
- [ ] Speaker deck reviewed by Brian (any pricing slide needs sign-off
      since it touches `sales/discount-matrix.md` numbers)
- [ ] Registration page load-tested; last year's webinar landing page went
      down for 12 minutes during the pre-registration push

## UTM scheme

Standardized on `utm_source=webinar`, `utm_campaign=q3-teambrain`,
`utm_medium=email` so landing-page conversions attribute correctly back to
the nurture sequence. Sales pulls the same UTM fields into deal source
tracking — see `sales/deal-desk-policy.md` for how webinar-sourced leads
get routed.

## Day-of

- [ ] Status page monitored during the live session (webinar traffic has
      caused two Sev-2 latency spikes on invoicing-api in the past)
- [ ] Follow-up email queued for 2 hours post-webinar, not next-day —
      2-hour follow-up converted 2.3x better in the Q2 test
      (`marketing/campaign-retro-q2-outbound.md`)

## Post-launch (T+1 week)

- [ ] Retro scheduled, results logged in
      `marketing/campaign-retro-q3-webinar.md`
- [ ] Attendee list handed to sales with UTM-tagged lead source, sorted by
      engagement score

Last run (Q3 2026): landing page converted at 14% off the nurture
sequence, well above the 9% campaign-average baseline.
