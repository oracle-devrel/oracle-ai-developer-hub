import type { ApiClient } from "../api/client.js";

export function fakeApi(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    getStatus: async () => ({ api: "ok", setup: { mode: "demo", oracleConfigured: true, openAIConfigured: false, missingVariables: [], collectionName: "MEM0_TS_LOCAL_DEMO", embeddingModel: "deterministic-demo", embeddingDimension: 24, chatModel: "none", createVectorIndex: true }, database: { connected: true, detail: "Oracle Database 23ai Free" } }),
    chat: async ({ userId }) => ({ userId, answer: "Your preferred drink is tea.", retrievedMemories: [{ id: "m1", userId, memory: "Prefers masala tea", score: 0.91, metadata: {} }], memoryEvents: [] }),
    listMemories: async (userId) => [{ id: "m1", userId, memory: "Prefers masala tea", metadata: { source: "seed" } }],
    createMemory: async () => [], updateMemory: async () => undefined, deleteMemory: async () => undefined,
    inspect: async () => ({ collectionName: "MEM0_TS_MEMORY_DEMO", exists: true, rowCount: 2, columns: [], vectorIndexes: [], samples: [] }),
    seed: async () => ({ added: 4 }), reset: async () => ({ collectionName: "MEM0_TS_MEMORY_DEMO", dropped: [] }),
    ...overrides,
  };
}
