# On-call rotation and escalation

The on-call rotation runs weekly, handed over every Monday at 10:00. Primary
on-call acknowledges pages within 5 minutes; if unacked after 10 minutes it
escalates to the secondary, then to the engineering lead.

Severity 1 (customer-facing outage) also opens an incident channel and pings
the incident commander. Postmortems are due within 48 hours and are blameless.

The escalation policy lives in PagerDuty under "Platform - Prod".
