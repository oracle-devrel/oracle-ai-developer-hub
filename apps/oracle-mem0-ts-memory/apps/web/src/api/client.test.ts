import { describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "./client.js";

describe("API client", () => {
  it("encodes memory search parameters", async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({ userId: "alice", memories: [] }), { status: 200 }));
    await createApiClient("", fetcher).listMemories("alice+demo", "tea & spice");
    expect(fetcher.mock.calls[0]?.[0]).toBe("/api/memories?userId=alice%2Bdemo&limit=20&query=tea+%26+spice");
  });

  it("turns public API failures into typed errors", async () => {
    const client = createApiClient("", async () => new Response(JSON.stringify({ error: "Oracle is unavailable" }), { status: 502 }));
    await expect(client.inspect()).rejects.toEqual(expect.objectContaining({ message: "Oracle is unavailable", status: 502 }));
  });
});
