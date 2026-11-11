import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { fakeApi } from "../../test/fixtures.js";
import { OracleInspector } from "./OracleInspector.js";

describe("OracleInspector", () => {
  it("reports the collection and row count", async () => {
    render(<OracleInspector api={fakeApi()} />);
    expect(await screen.findByText("MEM0_TS_MEMORY_DEMO")).toBeVisible();
    expect(screen.getByText("2 rows")).toBeVisible();
  });
});
