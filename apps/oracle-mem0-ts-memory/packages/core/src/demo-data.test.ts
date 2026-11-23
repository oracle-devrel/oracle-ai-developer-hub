import { describe, expect, it, vi } from "vitest";
import { DEMO_MEMORIES, seedDemoMemories } from "./demo-data.js";

describe("demo data", () => {
  it("seeds distinct user-scoped memories with provenance", async () => {
    const create = vi.fn(async () => []);
    const list = vi.fn(async () => []);
    const result = await seedDemoMemories({ create, list } as never);
    expect(result).toEqual({ added: 10 });
    expect(create).toHaveBeenCalledWith("user-1", expect.any(String), { source: "seed", demo: true, category: expect.any(String) });
    expect(new Set(DEMO_MEMORIES.map((item) => item.userId))).toEqual(new Set(["user-1", "user-2"]));
    expect(DEMO_MEMORIES.filter((item) => item.userId === "user-1")).toHaveLength(5);
    expect(DEMO_MEMORIES.filter((item) => item.userId === "user-2")).toHaveLength(5);
    expect(new Set(DEMO_MEMORIES.map((item) => item.category))).toEqual(
      new Set(["food", "travel", "schedule", "communication", "work"]),
    );
  });

  it("does not duplicate demo memories that already exist for a user", async () => {
    const existing = DEMO_MEMORIES.filter((item) => item.userId === "user-1")
      .map((item, index) => ({ id: `m${index}`, memory: item.text }));
    const list = vi.fn(async (userId: string) => userId === "user-1" ? existing : []);
    const create = vi.fn(async () => []);

    await expect(seedDemoMemories({ create, list } as never)).resolves.toEqual({ added: 5 });
    expect(create).not.toHaveBeenCalledWith("user-1", expect.anything(), expect.anything());
    expect(create).toHaveBeenCalledTimes(5);
  });
});
