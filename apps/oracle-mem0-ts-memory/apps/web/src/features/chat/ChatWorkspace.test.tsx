import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { fakeApi } from "../../test/fixtures.js";
import { ChatWorkspace } from "./ChatWorkspace.js";

describe("ChatWorkspace", () => {
  it("shows the answer and retrieved Oracle evidence", async () => {
    render(<ChatWorkspace api={fakeApi()} userId="alice" />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Message"), "What do I drink?");
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Your preferred drink is tea.")).toBeVisible();
    expect(screen.getByText("Prefers masala tea")).toBeVisible();
  });

  it("offers a user-specific starter prompt", async () => {
    render(<ChatWorkspace api={fakeApi()} userId="user-1" />);
    const starter = screen.getByRole("button", { name: "What drink do I prefer, and where should I sit when travelling?" });
    await userEvent.setup().click(starter);
    expect(screen.getByLabelText("Message")).toHaveValue("What drink do I prefer, and where should I sit when travelling?");
  });
});
