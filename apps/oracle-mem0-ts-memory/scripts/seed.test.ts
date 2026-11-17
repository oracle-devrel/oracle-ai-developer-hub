import { describe, expect, it } from "vitest";
import { DEMO_MEMORIES } from "@oracle-mem0-ts-memory/core";

describe("demo seed manifest", () => {
  it("contains unique, categorized memories for User 1 and User 2", () => {
    expect(DEMO_MEMORIES).toHaveLength(10);
    expect(new Set(DEMO_MEMORIES.map((item) => item.userId))).toEqual(new Set(["user-1", "user-2"]));
    expect(new Set(DEMO_MEMORIES.map((item) => item.text)).size).toBe(DEMO_MEMORIES.length);
    expect(DEMO_MEMORIES.every((item) => item.category.length > 0)).toBe(true);
  });
});
