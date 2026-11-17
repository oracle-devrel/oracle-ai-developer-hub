# API reference

All JSON endpoints are under `/api`. Validation errors return `400`; missing scoped memories return `404`; provider failures return a sanitized `502`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Process health check |
| `GET` | `/api/status` | Safe configuration and Oracle connectivity |
| `POST` | `/api/chat` | Retrieve memories and answer; only OpenAI mode infers new memories from the turn |
| `GET` | `/api/memories?userId=user-1&query=tea&limit=20` | List or vector-search scoped memories |
| `POST` | `/api/memories` | Add an explicit memory |
| `PUT` | `/api/memories/:id` | Update an owned memory |
| `DELETE` | `/api/memories/:id?userId=user-1` | Delete an owned memory |
| `GET` | `/api/inspect` | Inspect collection schema, indexes, counts, and safe samples |
| `POST` | `/api/seed` | Insert deterministic demo memories |
| `POST` | `/api/reset` | Drop only configured demo tables |

Example chat request:

```json
{ "userId": "user-1", "message": "What drink do I prefer?" }
```

The response includes `answer`, `retrievedMemories`, and `memoryEvents`. In default no-key mode, `memoryEvents` is empty because chat does not infer new facts; explicitly added memories remain available through `/api/memories`.
