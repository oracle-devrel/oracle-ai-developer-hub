import { describe, expect, it } from "vitest";
import { loadAppConfig } from "@oracle-mem0-ts-memory/db";

import { createMem0Config, normalizeMemoryResults } from "./mem0-client.js";

describe("createMem0Config", () => {
  it("uses local embeddings and a distinct Oracle collection without an API key", () => {
    const config = loadAppConfig({
      ORACLE_USER: "memory_user", ORACLE_PASSWORD: "secret", ORACLE_CONNECT_STRING: "localhost:1521/FREEPDB1",
    });
    const mem0 = createMem0Config(config);
    expect(mem0).toMatchObject({
      embedder: { provider: "langchain", config: { model: { embedQuery: expect.any(Function), embedDocuments: expect.any(Function) } } },
      llm: { provider: "langchain", config: { model: { invoke: expect.any(Function) } } },
      vectorStore: { provider: "oracledb", config: { collectionName: "MEM0_TS_LOCAL_DEMO", embeddingModelDims: 24 } },
    });
  });
});

describe("normalizeMemoryResults", () => {
  it("normalizes direct arrays and snake case fields", () => {
    expect(
      normalizeMemoryResults([
        { id: "m1", memory: "Likes tea", user_id: "alice", created_at: "2026-01-01", score: 0.8 },
      ]),
    ).toEqual([
      {
        id: "m1",
        memory: "Likes tea",
        userId: "alice",
        createdAt: "2026-01-01",
        score: 0.8,
        metadata: {},
      },
    ]);
  });

  it("normalizes results envelopes and camel case fields", () => {
    expect(
      normalizeMemoryResults({
        results: [{ id: "m2", memory: "Window seat", userId: "bob", updatedAt: "2026-01-02", metadata: { category: "travel" } }],
      }),
    ).toMatchObject([{ id: "m2", userId: "bob", updatedAt: "2026-01-02", metadata: { category: "travel" } }]);
  });

  it("accepts add-event payloads using event and data fields", () => {
    expect(
      normalizeMemoryResults({ results: [{ id: "m3", event: "ADD", data: "Prefers mornings", user_id: "alice" }] }),
    ).toMatchObject([{ id: "m3", memory: "Prefers mornings", userId: "alice" }]);
  });

  it("ignores malformed rows without ids or memory text", () => {
    expect(normalizeMemoryResults({ results: [{ message: "updated" }, null] })).toEqual([]);
  });
});
