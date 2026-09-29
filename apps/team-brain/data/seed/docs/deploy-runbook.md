# Deploying the billing service

The billing service deploys to production via the `deploy-billing` GitHub
Action. It runs the migration step first (`alembic upgrade head`), then a
blue-green cutover. If the migration fails, the workflow halts before any
traffic shifts, so a bad migration never takes down production.

Rollback: re-run the action pinned to the previous release tag. The Stripe
webhook secret lives in the `billing-prod` secret group, not in the repo.

On-call owner: Alice.
