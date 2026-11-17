import { describe, expect, it, vi } from "vitest";

import type { MemoryPort } from "./mem0-client.js";
import { createMemoryService } from "./memory-service.js";

function fakePort(overrides: Partial<MemoryPort> = {}): MemoryPort {
  return {
    add: vi.fn().mockResolvedValue([]),
    search: vi.fn().mockResolvedValue([]),
    getAll: vi.fn().mockResolvedValue([]),
    update: vi.fn().mockResolvedValue(undefined),
    delete: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("memory service", () => {
  it("creates an exact explicit memory without inference", async () => {
    const port = fakePort();
    await createMemoryService(port).create(" alice ", "Likes tea", { category: "food" });
    expect(port.add).toHaveBeenCalledWith("Likes tea", {
      userId: "alice",
      infer: false,
      metadata: { category: "food" },
    });
  });

  it("scopes list and search to the same user", async () => {
    const port = fakePort();
    const service = createMemoryService(port);
    await service.list("alice");
    await service.search("alice", "food", 200);
    expect(port.getAll).toHaveBeenCalledWith({ filters: { user_id: "alice" }, topK: 20 });
    expect(port.search).toHaveBeenCalledWith("food", { filters: { user_id: "alice" }, topK: 20 });
  });

  it("rejects blank users before calling Mem0", async () => {
    const port = fakePort();
    await expect(createMemoryService(port).list("   ")).rejects.toThrow(/user id/i);
    expect(port.getAll).not.toHaveBeenCalled();
  });

  it("updates a memory only when it belongs to the user", async () => {
    const own = { id: "m1", memory: "Tea", userId: "alice", metadata: {} };
    const port = fakePort({ getAll: vi.fn().mockResolvedValue([own]) });
    await createMemoryService(port).update("alice", "m1", "Green tea");
    expect(port.update).toHaveBeenCalledWith("m1", "Green tea");
  });

  it("does not reveal or mutate a cross-user memory", async () => {
    const port = fakePort({ getAll: vi.fn().mockResolvedValue([]) });
    const service = createMemoryService(port);
    await expect(service.update("alice", "bob-memory", "changed")).rejects.toMatchObject({ name: "NotFoundError" });
    await expect(service.remove("alice", "bob-memory")).rejects.toMatchObject({ name: "NotFoundError" });
    expect(port.update).not.toHaveBeenCalled();
    expect(port.delete).not.toHaveBeenCalled();
  });
});
