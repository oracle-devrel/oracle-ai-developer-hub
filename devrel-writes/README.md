# DevRel Articles for OCI Generative AI JET UI

This directory houses platform-optimized developer-relations content derived from this repository. It follows the workflow and guardrails under `.clinerules/` and enforces the branding requirement to use the exact product name “Oracle AI Database” in all user-facing content.

## Source of Truth

- Workflow: [.clinerules/workflows/devrel-content.md](../.clinerules/workflows/devrel-content.md)
- Branding rule: [.clinerules/branding-oracle-ai-database.md](../.clinerules/branding-oracle-ai-database.md)
- Context & platform guidance: [.clinerules/contextPrompt.md](../.clinerules/contextPrompt.md)
- Contribution guardrails: [.clinerules/contribution-guardrails.md](../.clinerules/contribution-guardrails.md)
- Secrets policy: [.clinerules/secrets-and-credentials-handling.md](../.clinerules/secrets-and-credentials-handling.md)

## Directory Structure

```
devrel-writes/
├── oci-genai-jet-ui/
│   ├── medium-article.md
│   ├── devto-article.md
│   └── datacamp-article.md
└── README.md
```

Additional topic folders may be added following `.clinerules/contextPrompt.md` patterns.

## Quick-Start Checklist

- Branding
  - Use “Oracle AI Database” exactly.
  - Do not use legacy/versioned names like “Oracle Database 23ai” or “26ai”.
  - If versions must be mentioned for compatibility, phrase as: “Oracle AI Database (version details for compatibility only)”.

- Security and Secrets
  - Do not include real credentials, tokens, ADB wallet files, or private endpoints.
  - Use clear placeholders only (e.g., `"ocid1.compartment.oc1..example"`).
  - See [.clinerules/secrets-and-credentials-handling.md](../.clinerules/secrets-and-credentials-handling.md).

- Minimal-Diff, Runnable Examples
  - Pull code snippets directly from this repo: `app/**`, `backend/**`, `deploy/**`, `scripts/**`.
  - Avoid changing repository config or behavior in examples.
  - Prefer small, annotated snippets with purpose, inputs, outputs.

- Cross-Link Core Docs
  - [README.md](../README.md)
  - [MODELS.md](../MODELS.md)
  - [RAG.md](../RAG.md)
  - [SERVICES_GUIDE.md](../SERVICES_GUIDE.md)
  - [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
  - [LOCAL.md](../LOCAL.md)

- LLM-Optimized Authoring (recommended)
  - Include structured JSON examples.
  - Provide Q&A pairs for key steps.
  - Use Mermaid diagrams for architecture.
  - Number hands-on steps clearly.

## Platform Templates

Use the templates embedded in the workflow:
- Medium: narrative, thought leadership, 1500–2500 words.
- dev.to: code-focused deep-dive, 1200–2000 words.
- DataCamp: step-by-step learning path, 1800–2500 words.

See: [.clinerules/workflows/devrel-content.md](../.clinerules/workflows/devrel-content.md)

## Process

1) Select platform and topic under `devrel-writes/`.
2) Start from the platform template file and fill in:
   - A hook (Medium), a crisp problem statement (dev.to), or learning goals (DataCamp).
   - Accurate code snippets from the repo with annotations.
   - Mermaid architecture where helpful.
   - Links to relevant repo docs.
3) Validate:
   - Branding compliance, secrets placeholders only.
   - Snippet accuracy and relative paths.
   - Spellcheck and link checks where available.
4) Prepare PR:
   - Include screenshots/diagram previews.
   - Reference the workflow and branding rule.
   - Optional: Add a brief `CHANGES.md` entry if user-visible.

---

Disclaimer: All user-facing content must reference “Oracle AI Database” exactly. Version details, if present, are for compatibility only.
