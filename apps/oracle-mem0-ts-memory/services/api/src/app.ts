import { Hono } from "hono";
import { bodyLimit } from "hono/body-limit";

import type {
  AppStatus,
  ChatRequest,
  ChatResponse,
  JsonValue,
  MemoryRecord,
  OracleInspection,
  ResetResult,
  SetupState,
} from "@oracle-mem0-ts-memory/shared";
import {
  chatRequestSchema,
  memoryCreateSchema,
  memoryQuerySchema,
  memoryUpdateSchema,
} from "@oracle-mem0-ts-memory/shared";

import { publicError } from "./public-errors.js";

export interface ApiDependencies {
  setup: SetupState;
  checkDatabase(): Promise<string>;
  chat(request: ChatRequest): Promise<ChatResponse>;
  listMemories(userId: string, limit: number): Promise<MemoryRecord[]>;
  searchMemories(userId: string, query: string, limit: number): Promise<MemoryRecord[]>;
  createMemory(userId: string, text: string, metadata: Record<string, JsonValue>): Promise<MemoryRecord[]>;
  updateMemory(userId: string, id: string, text: string): Promise<void>;
  deleteMemory(userId: string, id: string): Promise<void>;
  inspect(): Promise<OracleInspection>;
  seed(): Promise<{ added: number }>;
  reset(): Promise<ResetResult>;
}

async function body(request: Request): Promise<unknown> {
  return request.json().catch(() => ({}));
}

function fail(c: Parameters<Parameters<Hono["onError"]>[0]>[1], error: unknown) {
  const result = publicError(error);
  return c.json(result.body, result.status);
}

export function createApp(deps: ApiDependencies): Hono {
  const app = new Hono();
  app.use("/api/*", bodyLimit({ maxSize: 64 * 1024, onError: (c) => c.json({ error: "Request body is too large" }, 413) }));

  app.get("/health", (c) => c.json({ ok: true, service: "oracle-mem0-ts-memory-api" }));
  app.get("/api/status", async (c) => {
    let database: AppStatus["database"];
    try {
      database = { connected: true, detail: await deps.checkDatabase() };
    } catch {
      database = { connected: false, detail: "Oracle connection failed. Check the app .env and database status." };
    }
    return c.json<AppStatus>({ api: "ok", setup: deps.setup, database });
  });

  app.post("/api/chat", async (c) => {
    try {
      return c.json(await deps.chat(chatRequestSchema.parse(await body(c.req.raw))));
    } catch (error) { return fail(c, error); }
  });

  app.get("/api/memories", async (c) => {
    try {
      const parsed = memoryQuerySchema.parse(c.req.query());
      const memories = parsed.query
        ? await deps.searchMemories(parsed.userId, parsed.query, parsed.limit)
        : await deps.listMemories(parsed.userId, parsed.limit);
      return c.json({ userId: parsed.userId, query: parsed.query, memories });
    } catch (error) { return fail(c, error); }
  });

  app.post("/api/memories", async (c) => {
    try {
      const parsed = memoryCreateSchema.parse(await body(c.req.raw));
      return c.json({ memories: await deps.createMemory(parsed.userId, parsed.text, parsed.metadata) }, 201);
    } catch (error) { return fail(c, error); }
  });

  app.put("/api/memories/:id", async (c) => {
    try {
      const parsed = memoryUpdateSchema.parse(await body(c.req.raw));
      await deps.updateMemory(parsed.userId, c.req.param("id"), parsed.text);
      return c.json({ message: "Memory updated" });
    } catch (error) { return fail(c, error); }
  });

  app.delete("/api/memories/:id", async (c) => {
    try {
      const parsed = memoryQuerySchema.pick({ userId: true }).parse(c.req.query());
      await deps.deleteMemory(parsed.userId, c.req.param("id"));
      return c.json({ message: "Memory deleted" });
    } catch (error) { return fail(c, error); }
  });

  app.get("/api/inspect", async (c) => {
    try { return c.json(await deps.inspect()); } catch (error) { return fail(c, error); }
  });
  app.post("/api/seed", async (c) => {
    try { return c.json(await deps.seed()); } catch (error) { return fail(c, error); }
  });
  app.post("/api/reset", async (c) => {
    try { return c.json(await deps.reset()); } catch (error) { return fail(c, error); }
  });

  return app;
}
