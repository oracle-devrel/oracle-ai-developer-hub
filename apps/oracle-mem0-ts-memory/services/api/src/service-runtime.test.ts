import { describe, expect, it, vi } from "vitest";

import { createResettableServices } from "./service-runtime.js";

describe("resettable service runtime", () => {
  it("replaces provider state after the database collection is reset", async () => {
    const create = vi.fn()
      .mockReturnValueOnce({ generation: 1 })
      .mockReturnValueOnce({ generation: 2 });
    const runtime = createResettableServices(create);

    expect(runtime.current()).toEqual({ generation: 1 });
    await expect(runtime.reset(async () => ({ dropped: ["MEM0_TS_LOCAL_DEMO"] }))).resolves.toEqual({
      dropped: ["MEM0_TS_LOCAL_DEMO"],
    });
    expect(runtime.current()).toEqual({ generation: 2 });
  });

  it("keeps the existing services when resetting the collection fails", async () => {
    const create = vi.fn().mockReturnValue({ generation: 1 });
    const runtime = createResettableServices(create);

    await expect(runtime.reset(async () => { throw new Error("reset failed"); })).rejects.toThrow("reset failed");
    expect(runtime.current()).toEqual({ generation: 1 });
    expect(create).toHaveBeenCalledTimes(1);
  });
});
