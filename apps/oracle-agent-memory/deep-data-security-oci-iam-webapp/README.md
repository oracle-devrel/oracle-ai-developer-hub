# OCI IAM and Deep Data Security memory web app

> **Learning example only. This is not production-ready application code.**

Read [SECURITY.md](SECURITY.md) before configuring or running the example. It
describes the example's trust boundaries, destructive setup operations, and
security topics that are starting points for reviewing any adapted deployment.

This small Flask application accompanies the Oracle Agent Memory how-to guide.
After OCI IAM login, it shows the memories visible to the current identity and
allows the user to attempt to add a memory for any username. Oracle Deep Data
Security, not the web route, rejects cross-user writes.

The project includes its own standalone database utilities:

| Script | Purpose |
| --- | --- |
| `database_scripts/db_ociiam_setup.sh` | Enables OCI IAM external authentication and replaces the database OCI IAM credential. |
| `database_scripts/db_deepsec_user_setup.sh` | Creates the schema-owner and app-pool accounts and grants their required privileges. |
| `database_scripts/db_list_all_data_roles.sh` | Reads the current Deep Data Security roles, mappings, grants, predicates, and protected objects. |

The private `database_scripts/_common.sh` helper loads `.deepsec.env`, validates
required settings, and configures `TNS_ADMIN` when requested. These scripts are
part of this documentation project and do not depend on the repository test
suite.

The setup commands change database-wide authentication or account state. Read
them before running them and use a dedicated non-production database. For
clarity, the account script expects both users to be absent and stops if either
`CREATE USER` statement fails.

The template uses Autonomous Database `ADMIN` for setup. A different security
administrator needs user-management and grant authority plus the cross-schema
Deep Data Security privileges documented in the accompanying how-to.

From the extracted `deepsec_oci_iam_webapp` directory:

```bash
cp deepsec.env.example .deepsec.env
cp deepsec.runtime.env.example .deepsec.runtime.env
# Populate both files, then configure the database accounts and OCI IAM trust.
bash database_scripts/db_ociiam_setup.sh
bash database_scripts/db_deepsec_user_setup.sh

uv sync
uv run python scripts/setup_memory.py
uv run python run.py
```

Follow the accompanying Oracle Agent Memory how-to guide for the complete
identity-domain and database instructions.
