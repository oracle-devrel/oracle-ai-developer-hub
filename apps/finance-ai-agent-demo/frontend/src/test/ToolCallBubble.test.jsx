/**
 * Tests for ToolCallBubble rendering the suggest_portfolio_hedge tool call.
 *
 * Covers:
 * - Running state (spinner, no output toggle)
 * - Success state (tick, elapsed time, expandable output)
 * - Error state (cross icon, output visible)
 * - Output expand/collapse toggle
 * - Pretty-printed JSON output for hedge results
 * - Args rendered correctly in the header
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ToolCallBubble from "../components/ToolCallBubble";
import { makeToolCall, makeRunningToolCall, makeErrorToolCall, hedgeOutput } from "./hedgeFixtures";

// ---------------------------------------------------------------------------
// Running state
// ---------------------------------------------------------------------------

describe("ToolCallBubble — running state", () => {
  it("shows tool name and account_id arg in header", () => {
    render(<ToolCallBubble toolCall={makeRunningToolCall()} />);
    expect(screen.getByText(/suggest_portfolio_hedge/)).toBeInTheDocument();
    expect(screen.getByText(/account_id="ACC-001"/)).toBeInTheDocument();
  });

  it("renders a spinner element (animate-spin class)", () => {
    const { container } = render(<ToolCallBubble toolCall={makeRunningToolCall()} />);
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("does not show elapsed time while running", () => {
    render(<ToolCallBubble toolCall={makeRunningToolCall()} />);
    expect(screen.queryByText(/ms/)).not.toBeInTheDocument();
  });

  it("does not show output toggle while running", () => {
    render(<ToolCallBubble toolCall={makeRunningToolCall()} />);
    expect(screen.queryByText(/output/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Success state
// ---------------------------------------------------------------------------

describe("ToolCallBubble — success state", () => {
  it("shows tool name in header", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    expect(screen.getByText(/suggest_portfolio_hedge/)).toBeInTheDocument();
  });

  it("renders risk_focus arg in header", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    expect(screen.getByText(/risk_focus="all"/)).toBeInTheDocument();
  });

  it("shows elapsed time", () => {
    render(<ToolCallBubble toolCall={makeToolCall({ elapsed_ms: 142 })} />);
    expect(screen.getByText(/142ms/)).toBeInTheDocument();
  });

  it("shows success checkmark (✓)", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    // ✓ is rendered as &#10003; which is the Unicode CHECK MARK
    expect(screen.getByText("✓")).toBeInTheDocument();
  });

  it("shows 'Show output' button when output is present", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    expect(screen.getByText(/show output/i)).toBeInTheDocument();
  });

  it("output is collapsed by default", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    expect(screen.queryByText(/hedge_recommendations/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Output expand / collapse
// ---------------------------------------------------------------------------

describe("ToolCallBubble — expand/collapse output", () => {
  it("expands output on 'Show output' click", () => {
    const { container } = render(<ToolCallBubble toolCall={makeToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    // Pretty-printed JSON inside the <pre> block should contain hedge_recommendations
    const pre = container.querySelector("pre");
    expect(pre).toBeInTheDocument();
    expect(pre.textContent).toContain("hedge_recommendations");
  });

  it("shows 'Hide output' after expanding", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    expect(screen.getByText(/hide output/i)).toBeInTheDocument();
  });

  it("collapses output on second click", () => {
    const { container } = render(<ToolCallBubble toolCall={makeToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    fireEvent.click(screen.getByText(/hide output/i));
    // The <pre> block should be gone after collapsing
    expect(container.querySelector("pre")).not.toBeInTheDocument();
    expect(screen.getByText(/show output/i)).toBeInTheDocument();
  });

  it("pretty-prints hedge recommendation JSON when expanded", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    expect(screen.getByText(/hedge_recommendations/)).toBeInTheDocument();
    expect(screen.getByText(/risk_factors_identified/)).toBeInTheDocument();
  });

  it("shows disclaimer text when expanded", () => {
    render(<ToolCallBubble toolCall={makeToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    expect(screen.getByText(/algorithmically/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

describe("ToolCallBubble — error state", () => {
  it("shows error cross (✗) icon", () => {
    render(<ToolCallBubble toolCall={makeErrorToolCall()} />);
    expect(screen.getByText("✗")).toBeInTheDocument();
  });

  it("shows elapsed time on error", () => {
    render(<ToolCallBubble toolCall={makeErrorToolCall({ elapsed_ms: 55 })} />);
    expect(screen.getByText(/55ms/)).toBeInTheDocument();
  });

  it("shows error output when expanded", () => {
    render(<ToolCallBubble toolCall={makeErrorToolCall()} />);
    fireEvent.click(screen.getByText(/show output/i));
    expect(screen.getByText(/Database connection failed/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Args rendering edge cases
// ---------------------------------------------------------------------------

describe("ToolCallBubble — args rendering", () => {
  it("renders only account_id when risk_focus is omitted", () => {
    const toolCall = makeToolCall({ args: { account_id: "ACC-007" } });
    render(<ToolCallBubble toolCall={toolCall} />);
    expect(screen.getByText(/account_id="ACC-007"/)).toBeInTheDocument();
  });

  it("renders both args when risk_focus is provided", () => {
    const toolCall = makeToolCall({
      args: { account_id: "ACC-003", risk_focus: "sector" },
    });
    render(<ToolCallBubble toolCall={toolCall} />);
    expect(screen.getByText(/risk_focus="sector"/)).toBeInTheDocument();
  });

  it("handles empty args object gracefully", () => {
    const toolCall = makeToolCall({ args: {} });
    render(<ToolCallBubble toolCall={toolCall} />);
    // Should render tool name with empty parens, no crash
    expect(screen.getByText(/suggest_portfolio_hedge/)).toBeInTheDocument();
  });

  it("handles null args gracefully", () => {
    const toolCall = makeToolCall({ args: null });
    render(<ToolCallBubble toolCall={toolCall} />);
    expect(screen.getByText(/suggest_portfolio_hedge/)).toBeInTheDocument();
  });
});
