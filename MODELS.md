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
- capabilities (includes "CHAT" for chat-capable)
- timeCreated

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

## Parameter guidance

- temperature: 0.0 for summarization, ~0.5 for chat by default in this app; adjust per use case
- maxTokens: 600 by default; adjust to control response length and cost
- topP/topK: used where supported; consider starting with `topP` only for broader compatibility
- penalties:
  - frequencyPenalty: avoid for Grok; use conservatively for other vendors
  - presencePenalty: do not send to Grok; often optional for other vendors

If you encounter 400 errors with a specific parameter on a vendor, remove or tune that parameter. The backend already avoids sending known-incompatible parameters for Grok.

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
- Validate your embedding path quickly with: `GET /api/kb/diag/embed?text=test` (expect `ok: true`, `vectorLen ~ 1024`).

## Summarization model

- File summaries during upload use `genai.summarization_model_id`. This does not affect chat or embedding models.

## References

- RAG flow and API quick reference: see `RAG.md`.
- Recent changes and notes: see `CHANGES.md`.
