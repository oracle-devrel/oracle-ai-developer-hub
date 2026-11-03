import type { JsonValue, MemoryRecord } from "@oracle-mem0-ts-memory/shared";

import { NotFoundError } from "./errors.js";
import type { MemoryPort } from "./mem0-client.js";

export interface MemoryService {
  create(userId: string, text: string, metadata?: Record<string, JsonValue>): Promise<MemoryRecord[]>;
  list(userId: string, limit?: number): Promise<MemoryRecord[]>;
  search(userId: string, query: string, limit?: number): Promise<MemoryRecord[]>;
  update(userId: string, id: string, text: string): Promise<void>;
  remove(userId: string, id: string): Promise<void>;
}

function cleanUserId(value: string): string {
  const userId = value.trim();
  if (!userId) throw new Error("User id is required");
  return userId;
}

function cleanText(value: string, label: string): string {
  const text = value.trim();
  if (!text) throw new Error(`${label} is required`);
  return text;
}

function boundedLimit(limit = 20): number {
  return Math.max(1, Math.min(20, Math.trunc(limit)));
}

export function createMemoryService(port: MemoryPort): MemoryService {
  async function assertOwned(userId: string, id: string): Promise<void> {
    const memories = await port.getAll({ filters: { user_id: userId }, topK: 1_000 });
    if (!memories.some((memory) => memory.id === id)) throw new NotFoundError("Memory was not found");
  }

  return {
    async create(userId, text, metadata = {}) {
      const cleanUser = cleanUserId(userId);
      return port.add(cleanText(text, "Memory text"), { userId: cleanUser, infer: false, metadata });
    },
    async list(userId, limit) {
      const cleanUser = cleanUserId(userId);
      return port.getAll({ filters: { user_id: cleanUser }, topK: boundedLimit(limit) });
    },
    async search(userId, query, limit) {
      const cleanUser = cleanUserId(userId);
      return port.search(cleanText(query, "Search query"), {
        filters: { user_id: cleanUser },
        topK: boundedLimit(limit),
      });
    },
    async update(userId, id, text) {
      const cleanUser = cleanUserId(userId);
      await assertOwned(cleanUser, id);
      await port.update(id, cleanText(text, "Memory text"));
    },
    async remove(userId, id) {
      const cleanUser = cleanUserId(userId);
      await assertOwned(cleanUser, id);
      await port.delete(id);
    },
  };
}
