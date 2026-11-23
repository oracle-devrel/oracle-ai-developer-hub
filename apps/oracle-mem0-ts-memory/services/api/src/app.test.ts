import { describe, expect, it, vi } from "vitest";

import { createApp, type ApiDependencies } from "./app.js";

function dependencies(): ApiDependencies {
  return {
    setup: {
      mode: "openai",
      oracleConfigured: true,
      openAIConfigured: true,
      missingVariables: [],
      collectionName: "MEM0_TS_MEMORY_DEMO",
      embeddingModel: "text-embedding-3-small",
      embeddingDimension: 1536,
      chatModel: "gpt-4o-mini",
      createVectorIndex: false,
    },
    checkDatabase: vi.fn().mockResolvedValue("Oracle 26ai"),
    chat: vi.fn().mockResolvedValue({ userId: "alice", answer: "Hello", retrievedMemories: [], memoryEvents: [] }),
    listMemories: vi.fn().mockResolvedValue([]),
    searchMemories: vi.fn().mockResolvedValue([]),
    createMemory: vi.fn().mockResolvedValue([]),
    updateMemory: vi.fn().mockResolvedValue(undefined),
    deleteMemory: vi.fn().mockResolvedValue(undefined),
    inspect: vi.fn().mockResolvedValue({ collectionName: "MEM0_TS_MEMORY_DEMO", exists: true, rowCount: 0, columns: [], vectorIndexes: [], samples: [] }),
    seed: vi.fn().mockResolvedValue({ added: 4 }),
    reset: vi.fn().mockResolvedValue({ collectionName: "MEM0_TS_MEMORY_DEMO", dropped: [] }),
  };
}

describe("API", () => {
  it("does not enable cross-origin access in the same-origin production API", async () => {
    const response = await createApp(dependencies()).request("/health", { headers: { origin: "https://untrusted.example" } });
    expect(response.headers.get("access-control-allow-origin")).toBeNull();
  });
  it("reports health and configured database status", async () => {
    const app = createApp(dependencies());
    expect(await (await app.request("/health")).json()).toMatchObject({ ok: true });
    expect(await (await app.request("/api/status")).json()).toMatchObject({ database: { connected: true } });
  });

  it("validates and serves chat", async () => {
    const deps = dependencies();
    const app = createApp(deps);
    expect((await app.request("/api/chat", { method: "POST", body: "{}", headers: { "content-type": "application/json" } })).status).toBe(400);
    const response = await app.request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ userId: "alice", message: "Hello" }),
      headers: { "content-type": "application/json" },
    });
    expect(response.status).toBe(200);
    expect(deps.chat).toHaveBeenCalledWith({ userId: "alice", message: "Hello" });
  });

  it("lists or searches only with an explicit user", async () => {
    const deps = dependencies();
    const app = createApp(deps);
    expect((await app.request("/api/memories")).status).toBe(400);
    await app.request("/api/memories?userId=alice");
    await app.request("/api/memories?userId=alice&query=food&limit=3");
    expect(deps.listMemories).toHaveBeenCalledWith("alice", 10);
    expect(deps.searchMemories).toHaveBeenCalledWith("alice", "food", 3);
  });

  it("supports explicit memory CRUD", async () => {
    const deps = dependencies();
    const app = createApp(deps);
    const json = (value: unknown) => ({ body: JSON.stringify(value), headers: { "content-type": "application/json" } });
    expect((await app.request("/api/memories", { method: "POST", ...json({ userId: "alice", text: "Likes tea" }) })).status).toBe(201);
    expect((await app.request("/api/memories/m1", { method: "PUT", ...json({ userId: "alice", text: "Likes green tea" }) })).status).toBe(200);
    expect((await app.request("/api/memories/m1?userId=alice", { method: "DELETE" })).status).toBe(200);
  });

  it("does not accept a reset target from the caller", async () => {
    const deps = dependencies();
    const app = createApp(deps);
    const response = await app.request("/api/reset", {
      method: "POST",
      body: JSON.stringify({ collectionName: "SENSITIVE_TABLE" }),
      headers: { "content-type": "application/json" },
    });
    expect(response.status).toBe(200);
    expect(deps.reset).toHaveBeenCalledWith();
  });

  it("maps not-found and provider failures without leaking raw messages", async () => {
    const notFound = dependencies();
    notFound.updateMemory = vi.fn().mockRejectedValue(Object.assign(new Error("private details"), { name: "NotFoundError" }));
    const provider = dependencies();
    provider.chat = vi.fn().mockRejectedValue(Object.assign(new Error("secret upstream body"), { name: "ProviderPhaseError", phase: "generation" }));
    const body = { method: "PUT", body: JSON.stringify({ userId: "alice", text: "x" }), headers: { "content-type": "application/json" } };
    expect((await createApp(notFound).request("/api/memories/missing", body)).status).toBe(404);
    const response = await createApp(provider).request("/api/chat", { method: "POST", body: JSON.stringify({ userId: "alice", message: "hi" }), headers: { "content-type": "application/json" } });
    expect(response.status).toBe(502);
    expect(await response.text()).not.toContain("secret upstream body");
  });

  it("explains an expired embedding API key when loading demo memories", async () => {
    const deps = dependencies();
    deps.seed = vi.fn().mockRejectedValue(Object.assign(new Error("upstream secret details"), {
      status: 401,
      code: "expired_secret_key",
    }));

    const response = await createApp(deps).request("/api/seed", { method: "POST" });
    expect(response.status).toBe(502);
    const payload = await response.json() as { error: string };
    expect(payload.error).toMatch(/API key has expired/i);
    expect(payload.error).toMatch(/OPENAI_API_KEY.*\.env/i);
    expect(payload.error).not.toContain("upstream secret details");
  });

  it("explains exhausted API credits when loading demo memories", async () => {
    const deps = dependencies();
    deps.seed = vi.fn().mockRejectedValue(Object.assign(new Error("upstream private details"), {
      status: 429,
      code: "credit_balance_exhausted",
    }));

    const response = await createApp(deps).request("/api/seed", { method: "POST" });
    expect(response.status).toBe(502);
    const payload = await response.json() as { error: string };
    expect(payload.error).toMatch(/no API credits remaining/i);
    expect(payload.error).toMatch(/organization/i);
    expect(payload.error).not.toContain("upstream private details");
  });
});
