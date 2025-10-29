# Models and Parameters

This application calls OCI Generative AI Inference with vendor-aware request builders. It adapts parameters per vendor/model to prevent invalid-argument errors.

## Discovering available models

Use the backend endpoint to list models in your compartment (filtered to chat-capable models):
```bash
curl http://localhost:8080/api/genai/models
```

Response contains:
- id: model OCID
- displayName, vendor, version
- capabilities (e.g., "CHAT" for chat, "EMBED" for embeddings)
- timeCreated

Notes:
- Filter to chat-capable models in the UI using capability "CHAT".
- Use capability "EMBED" to choose an embedding model for KB ingestion and diagnostics.

Pass the `id` (model OCID) into requests such as POST `/api/genai/rag`.

## Vendor-specific behavior

The backend resolves vendor and uses the appropriate request type and parameters.

- Cohere
  - Request: `CohereChatRequest`
  - Typical params: `message`, `maxTokens`, `temperature`, `frequencyPenalty`, `topP`, `topK`, `isStream`
  - Notes: Cohere path is vendor-specific and does not use `GenericChatRequest`

- Meta
  - Request: `GenericChatRequest`
  - Typical params: `messages`, `maxTokens`, `temperature`, `topP`, `topK`, `isStream`
  - Notes: `presencePenalty` is not sent

- xAI (Grok)
  - Request: `GenericChatRequest`
  - Typical params: `messages`, `maxTokens`, `temperature`, `topP`, `isStream`
  - Not sent: `presencePenalty`, `frequencyPenalty`, `topK`
  - Reason: Grok models return 400 if unsupported parameters are included

## Defaults used by this app
- streaming: enabled in the UI where supported (`isStream: true`); REST curl examples return full responses
- temperature: 0.5 default for chat; 0.0 for summarization tasks
- maxTokens: 600 default; increase/decrease to control latency and cost
- topP/topK: prefer `topP` for broad compatibility; omit `topK` for Grok
- penalties: use `frequencyPenalty` conservatively; never send `presencePenalty` to Grok

## Parameter guidance

- temperature: 0.0 for summarization, ~0.5 for chat by default in this app; adjust per use case
- maxTokens: 600 by default; adjust to control response length and cost
- topP/topK: used where supported; consider starting with `topP` only for broader compatibility
- penalties:
  - frequencyPenalty: avoid for Grok; use conservatively for other vendors
  - presencePenalty: do not send to Grok; often optional for other vendors

If you encounter 400 errors with a specific parameter on a vendor, remove or tune that parameter. The backend already avoids sending known-incompatible parameters for Grok.

## Common errors and fixes
- 400 invalid parameter (Grok): remove `presencePenalty`, `frequencyPenalty`, `topK`
- 400 unsupported field (Meta/Cohere): ensure only supported fields for that vendor/request type
- 403/404 model not found: verify compartment access and the model OCID
- Timeouts/latency: lower `maxTokens`, consider disabling streaming in client, or choose a smaller/faster model

## Example flow

1) List models:
```bash
curl http://localhost:8080/api/genai/models
```

2) Pick an `id` for the model you want (e.g., a Cohere or Grok model OCID).

3) Ask RAG:
```bash
curl -X POST http://localhost:8080/api/genai/rag \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain section 2", "modelId": "ocid1.generativeaimodel.oc1...."}'
```

4) For plain chat/summarization without RAG, use your existing UI; the backend constructs vendor-aware requests behind the scenes.

## Notes on stability

- The backend enforces a minimal, compatible set of parameters per vendor to avoid 400 errors.
- If vendors change parameter support, adjust the request builders accordingly (in `OCIGenAIService`).
- See `TROUBLESHOOTING.md` for common error signatures and fixes.

## Embedding models and dimensions

- Embedding model is configured via `genai.embed_model_id` and is independent from the chat model.
- The KB schema uses `VECTOR(1024, FLOAT32)`. Prefer a 1024-dimension embedding model (e.g., `cohere.embed-english-v3.0`). If you choose a different dimension, update the Liquibase migration and the insertion paths accordingly.
- Validate embedding path: `GET /api/kb/diag/embed?text=test` → expect `ok: true`, `vectorLen ~ 1024`
- Check schema status: `GET /api/kb/diag/schema` → ensure KB tables and indexes exist

## Summarization model

- File summaries during upload use `genai.summarization_model_id`. This does not affect chat or embedding models.

## References

- RAG flow and API quick reference: see `RAG.md`
- Database schema and Liquibase: see `DATABASE.md`
- Kubernetes/OKE deployment: see `K8S.md`
- Recent changes and notes: see `CHANGES.md`
- Overview and architecture: see `README.md`
