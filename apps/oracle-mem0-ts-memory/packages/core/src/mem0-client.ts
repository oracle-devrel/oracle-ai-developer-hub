import { Memory } from "mem0ai/oss";

import type { AppConfig } from "@oracle-mem0-ts-memory/db";
import type { JsonValue, MemoryRecord } from "@oracle-mem0-ts-memory/shared";
import { DemoEmbeddings } from "./demo-embeddings.js";

export interface MemoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface MemoryPort {
  add(
    messages: string | MemoryMessage[],
    options: { userId: string; metadata?: Record<string, JsonValue>; infer?: boolean },
  ): Promise<MemoryRecord[]>;
  search(query: string, options: { filters: { user_id: string }; topK?: number }): Promise<MemoryRecord[]>;
  getAll(options: { filters: { user_id: string }; topK?: number }): Promise<MemoryRecord[]>;
  update(id: string, text: string): Promise<void>;
  delete(id: string): Promise<void>;
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

export function normalizeMemoryResults(value: unknown): MemoryRecord[] {
  const envelope = objectValue(value);
  const rows = Array.isArray(value) ? value : Array.isArray(envelope.results) ? envelope.results : [];
  return rows.flatMap((raw) => {
    const row = objectValue(raw);
    const id = typeof row.id === "string" ? row.id : "";
    const memory = typeof row.memory === "string" ? row.memory : typeof row.data === "string" ? row.data : "";
    if (!id || !memory) return [];
    const metadata = objectValue(row.metadata) as Record<string, JsonValue>;
    const userId = typeof row.userId === "string"
      ? row.userId
      : typeof row.user_id === "string"
        ? row.user_id
        : typeof metadata.user_id === "string"
          ? metadata.user_id
          : "";
    const result: MemoryRecord = { id, memory, userId, metadata };
    if (typeof row.score === "number") result.score = row.score;
    const createdAt = row.createdAt ?? row.created_at;
    const updatedAt = row.updatedAt ?? row.updated_at;
    if (typeof createdAt === "string") result.createdAt = createdAt;
    if (typeof updatedAt === "string") result.updatedAt = updatedAt;
    return [result];
  });
}

export function createMem0Config(config: AppConfig): ConstructorParameters<typeof Memory>[0] {
  return {
    llm: config.mode === "demo"
      ? { provider: "langchain", config: { model: {
        invoke: async () => { throw new Error("Demo mode does not perform LLM inference"); },
      } } }
      : { provider: "openai", config: { apiKey: config.openAI.apiKey, model: config.openAI.chatModel, temperature: 0.1 } },
    embedder: config.mode === "demo"
      ? { provider: "langchain", config: { model: new DemoEmbeddings() } }
      : { provider: "openai", config: {
        apiKey: config.openAI.apiKey, model: config.openAI.embeddingModel, embeddingDims: config.embeddingDimension,
      } },
    vectorStore: {
      provider: "oracledb",
      config: {
        collectionName: config.collectionName,
        embeddingModelDims: config.embeddingDimension,
        connectionParams: config.oracle,
        useConnectionPool: true,
        doCreateIndex: config.createVectorIndex,
        distanceMetric: "COSINE",
      },
    },
    disableHistory: true,
  };
}

export function createMem0Port(config: AppConfig): MemoryPort {
  process.env.MEM0_TELEMETRY = "false";
  const memory = new Memory(createMem0Config(config));

  return {
    async add(messages, options) {
      return normalizeMemoryResults(await memory.add(messages, options));
    },
    async search(query, options) {
      return normalizeMemoryResults(await memory.search(query, options));
    },
    async getAll(options) {
      return normalizeMemoryResults(await memory.getAll(options));
    },
    async update(id, text) {
      await memory.update(id, { text });
    },
    async delete(id) {
      await memory.delete(id);
    },
  };
}
