# Campaign retro: Q3 webinar

Owner: Julia. Ran per `marketing/launch-checklist-q3-webinar.md`,
August 2026, 612 registrants, 340 live attendees.

## Results

- Landing page conversion: 14% off the nurture sequence (UTM scheme:
  `utm_source=webinar`, `utm_campaign=q3-teambrain`, `utm_medium=email`),
  beating the 9% campaign-average baseline referenced in the checklist.
- 2-hour post-webinar follow-up email (carried over from the Q2 outbound
  learning, `marketing/campaign-retro-q2-outbound.md`) drove 41% of total
  clicks, confirming that finding generalizes beyond cold outbound.
- Sales reported 22 sales-qualified leads from the attendee list, 6 already
  in active evaluation as of this retro.

## Issues

- Registration page briefly degraded (Sev-2, not the 12-minute outage from
  last year but a 4-minute elevated-latency window) during the
  pre-registration push — invoicing-api's rate limit kicked in because the
  registration flow shares an API key with a demo integration. Ticketed to
  move the demo integration to its own key before the next webinar.
- Two attendees asked directly about our discount structure during Q&A;
  the speaker correctly deferred to "talk to your account rep" rather than
  quoting numbers, per `marketing/brand-voice-guide.md`.

## Next steps

1. Separate API key for the demo integration before Q4 webinar (owner:
   Julia, filed with engineering).
2. Test a 3-touch pre-webinar reminder sequence instead of 2 — open
   question for the next retro.
3. Q4 webinar topic candidates due from Julia by end of September.
