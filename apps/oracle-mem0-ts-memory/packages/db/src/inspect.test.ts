import { describe, expect, it, vi } from "vitest";

import { inspectCollection } from "./inspect.js";

describe("inspectCollection", () => {
  it("returns collection metadata and safe payload samples", async () => {
    const query = vi.fn()
      .mockResolvedValueOnce([{ count: 1 }])
      .mockResolvedValueOnce([{ row_count: 2 }])
      .mockResolvedValueOnce([{ name: "VECTOR", data_type: "VECTOR", nullable: "Y" }])
      .mockResolvedValueOnce([{ name: "MEM0_TS_IDX", type: "VECTOR", status: "VALID" }])
      .mockResolvedValueOnce([
        { id: "m1", payload: { data: "Likes tea", user_id: "alice", api_key: "hidden", category: "food" } },
      ]);

    const result = await inspectCollection("MEM0_TS_MEMORY_DEMO", query);

    expect(result).toMatchObject({ exists: true, rowCount: 2 });
    expect(result.samples[0]).toEqual({
      id: "m1",
      memory: "Likes tea",
      userId: "alice",
      metadata: { category: "food" },
    });
    expect(query).toHaveBeenCalledTimes(5);
  });

  it("returns an empty inspection when the collection does not exist", async () => {
    const query = vi.fn().mockResolvedValueOnce([{ count: 0 }]);
    await expect(inspectCollection("MEM0_TS_MEMORY_DEMO", query)).resolves.toMatchObject({
      exists: false,
      rowCount: 0,
      samples: [],
    });
  });
});
