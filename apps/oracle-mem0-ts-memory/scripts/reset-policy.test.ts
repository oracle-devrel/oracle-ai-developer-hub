import { describe, expect, it } from "vitest";
import { canResetWithoutPrompt } from "./reset-policy.js";

describe("reset CLI policy", () => {
  it("requires --yes when no interactive terminal is attached", () => {
    expect(canResetWithoutPrompt(["node", "reset.ts"], false)).toBe(false);
    expect(canResetWithoutPrompt(["node", "reset.ts", "--yes"], false)).toBe(true);
  });
});
