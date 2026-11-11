import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { fakeApi } from "../../test/fixtures.js";
import { MemoryExplorer } from "./MemoryExplorer.js";

describe("MemoryExplorer", () => {
  it("lists scoped memories and can delete one", async () => {
    const deleteMemory = vi.fn(async () => undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<MemoryExplorer api={fakeApi({ deleteMemory })} userId="alice" />);
    expect(await screen.findByText("Prefers masala tea")).toBeVisible();
    await userEvent.setup().click(screen.getByRole("button", { name: "Delete memory" }));
    expect(deleteMemory).toHaveBeenCalledWith("alice", "m1");
  });

  it("updates a memory from the edit action", async () => {
    const updateMemory = vi.fn(async () => undefined);
    vi.spyOn(window, "prompt").mockReturnValue("Prefers green tea");
    render(<MemoryExplorer api={fakeApi({ updateMemory })} userId="alice" />);

    await userEvent.setup().click(await screen.findByRole("button", { name: "Edit memory" }));

    expect(updateMemory).toHaveBeenCalledWith("alice", "m1", "Prefers green tea");
  });
});
