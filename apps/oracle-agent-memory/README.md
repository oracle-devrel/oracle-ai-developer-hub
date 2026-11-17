# Oracle AI Agent Memory examples

This directory hosts Oracle AI Agent Memory examples demonstrating how to add persistent memory to applications and agent harnesses with Oracle AI Database 26ai. Each entry links directly to its source folder; packaged downloads are available for the examples used by externally hosted documentation.

| Title | Stack | Highlights | Path |
| ----- | ----- | ---------- | ---- |
| Social-media Voice Agent | Node.js, Express, React, Vite, OCI Generative AI, Oracle AI Database | Learns a user's writing voice through episodic, semantic, and reflection memory. | [Open](./social-media-voice-agent) |
| Codex Plugin | Python, MCP, Codex hooks, Oracle AI Agent Memory | Exposes manual memory tools to Codex and optionally captures session messages through hooks. | [Open](./codex-plugin) · [Download ZIP](./_downloads/codex-plugin.zip?raw=1) |
| OCI IAM and Deep Data Security Web App | Python, Flask, OCI IAM, Oracle Deep Data Security, Oracle AI Agent Memory | Enforces identity-scoped access to memories, including database-enforced rejection of cross-user writes. | [Open](./deep-data-security-oci-iam-webapp) · [Download ZIP](./_downloads/deep-data-security-oci-iam-webapp.zip?raw=1) |

The ZIP archives are packaged copies of their adjacent source directories. Regenerate an archive whenever its source changes.

The Codex plugin and OCI IAM / Deep Data Security web app are learning examples, not production-ready deployments. Read the `SECURITY.md` file in each example before configuring or running it. The Deep Data Security setup can change database-wide authentication and account state; use a dedicated non-production database.
