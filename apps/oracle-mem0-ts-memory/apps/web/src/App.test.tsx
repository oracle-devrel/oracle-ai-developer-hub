import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { fakeApi } from "./test/fixtures.js";
import { App } from "./App.js";

describe("App shell", () => {
  beforeEach(() => window.localStorage.clear());
  it("presents an Oracle-first guided demo and persists the selected numbered user", async () => {
    const api = fakeApi();
    render(<App client={api} />);

    expect(await screen.findByText("Oracle Database connected")).toBeVisible();
    expect(screen.getByText("No-key demo mode")).toBeVisible();
    expect(screen.queryByText(/OpenAI/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/gpt-4/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Try the demo" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Load demo memories" })).toBeVisible();

    await userEvent.setup().selectOptions(screen.getByLabelText("Demo user"), "user-2");
    expect(window.localStorage.getItem("mem0-demo-user")).toBe("user-2");
    expect(screen.getByRole("option", { name: "User 1" })).toBeVisible();
    expect(screen.getByRole("option", { name: "User 2" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Memory explorer" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Oracle inspector" })).toBeVisible();
  });

  it("shows a failed demo load beside the action that failed", async () => {
    const api = fakeApi({ seed: async () => { throw new Error("API key has expired. Update OPENAI_API_KEY in this app's .env and restart the API."); } });
    render(<App client={api} />);

    const button = screen.getByRole("button", { name: "Load demo memories" });
    await userEvent.setup().click(button);

    const step = button.closest("article");
    expect(step).not.toBeNull();
    expect(await within(step as HTMLElement).findByRole("alert")).toHaveTextContent(/API key has expired/i);
  });

  it("explains when the demo memories are already loaded", async () => {
    const api = fakeApi({ seed: async () => ({ added: 0 }) });
    render(<App client={api} />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Load demo memories" }));

    expect((await screen.findAllByText(/ten demo memories are already loaded/i))[0]).toBeVisible();
    expect(screen.queryByText("Loaded 0 demo memories. Choose a starter question below.")).not.toBeInTheDocument();
  });
});
