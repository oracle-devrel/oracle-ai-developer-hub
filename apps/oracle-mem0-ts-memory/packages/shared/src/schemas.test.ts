import { describe, expect, it } from "vitest";

import {
  chatRequestSchema,
  memoryCreateSchema,
  memoryQuerySchema,
} from "./schemas.js";

describe("shared request schemas", () => {
  it("trims and accepts a valid chat request", () => {
    expect(
      chatRequestSchema.parse({ userId: " alice ", message: " Remember this " }),
    ).toEqual({ userId: "alice", message: "Remember this" });
  });

  it.each([
    { userId: "", message: "Remember this" },
    { userId: "alice", message: "   " },
  ])("rejects an invalid chat request: %j", (value) => {
    expect(() => chatRequestSchema.parse(value)).toThrow();
  });

  it("rejects a memory query without a user id", () => {
    expect(() => memoryQuerySchema.parse({ query: "food" })).toThrow();
  });

  it("keeps metadata on an explicit memory", () => {
    expect(
      memoryCreateSchema.parse({
        userId: "alice",
        text: "Prefers window seats",
        metadata: { category: "travel" },
      }),
    ).toMatchObject({ metadata: { category: "travel" } });
  });
});
