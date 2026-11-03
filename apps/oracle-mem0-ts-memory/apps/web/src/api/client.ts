import type { AppStatus, ChatRequest, ChatResponse, JsonValue, MemoryRecord, OracleInspection, ResetResult } from "@oracle-mem0-ts-memory/shared";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

export interface ApiClient {
  getStatus(): Promise<AppStatus>;
  chat(request: ChatRequest): Promise<ChatResponse>;
  listMemories(userId: string, query?: string): Promise<MemoryRecord[]>;
  createMemory(userId: string, text: string, metadata?: Record<string, JsonValue>): Promise<MemoryRecord[]>;
  updateMemory(userId: string, id: string, text: string): Promise<void>;
  deleteMemory(userId: string, id: string): Promise<void>;
  inspect(): Promise<OracleInspection>;
  seed(): Promise<{ added: number }>;
  reset(): Promise<ResetResult>;
}

export function createApiClient(baseUrl = "", fetcher: typeof fetch = fetch): ApiClient {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetcher(`${baseUrl}${path}`, { headers: { "content-type": "application/json", ...init?.headers }, ...init });
    const payload = await response.json().catch(() => ({})) as { error?: string };
    if (!response.ok) throw new ApiError(payload.error ?? `Request failed (${response.status})`, response.status);
    return payload as T;
  }
  return {
    getStatus: () => request("/api/status"),
    chat: (value) => request("/api/chat", { method: "POST", body: JSON.stringify(value) }),
    async listMemories(userId, query) {
      const params = new URLSearchParams({ userId, limit: "20" });
      if (query) params.set("query", query);
      const result = await request<{ memories: MemoryRecord[] }>(`/api/memories?${params}`);
      return result.memories;
    },
    async createMemory(userId, text, metadata = {}) {
      const result = await request<{ memories: MemoryRecord[] }>("/api/memories", { method: "POST", body: JSON.stringify({ userId, text, metadata }) });
      return result.memories;
    },
    updateMemory: async (userId, id, text) => { await request(`/api/memories/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify({ userId, text }) }); },
    deleteMemory: async (userId, id) => { await request(`/api/memories/${encodeURIComponent(id)}?userId=${encodeURIComponent(userId)}`, { method: "DELETE" }); },
    inspect: () => request("/api/inspect"),
    seed: () => request("/api/seed", { method: "POST" }),
    reset: () => request("/api/reset", { method: "POST" }),
  };
}
