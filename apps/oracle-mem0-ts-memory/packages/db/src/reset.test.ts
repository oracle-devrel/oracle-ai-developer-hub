import { describe, expect, it, vi } from "vitest";

import { resetDemoCollection } from "./reset.js";

describe("resetDemoCollection", () => {
  it("drops only the configured demo and entity collections", async () => {
    const execute = vi.fn().mockResolvedValue(undefined);
    await expect(resetDemoCollection("MEM0_TS_MEMORY_DEMO", execute)).resolves.toEqual({
      collectionName: "MEM0_TS_MEMORY_DEMO",
      dropped: ["MEM0_TS_MEMORY_DEMO", "MEM0_TS_MEMORY_DEMO_ENTITY"],
    });
    expect(execute).toHaveBeenCalledTimes(2);
  });

  it("ignores only Oracle table-not-found errors", async () => {
    const missing = Object.assign(new Error("missing"), { errorNum: 942 });
    await expect(resetDemoCollection("MEM0_TS_MEMORY_DEMO", vi.fn().mockRejectedValue(missing))).resolves.toEqual({
      collectionName: "MEM0_TS_MEMORY_DEMO",
      dropped: [],
    });
    await expect(resetDemoCollection("MEM0_TS_MEMORY_DEMO", vi.fn().mockRejectedValue(new Error("denied")))).rejects.toThrow("denied");
  });

  it("refuses non-demo collection names", async () => {
    await expect(resetDemoCollection("CUSTOM_TABLE", vi.fn())).rejects.toThrow(/demo collection/i);
  });
});
