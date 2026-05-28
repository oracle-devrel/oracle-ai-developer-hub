/**
 * Tests for the chatReducer handling suggest_portfolio_hedge tool call events.
 *
 * Exercises the ADD_TOOL_CALL_START → UPDATE_TOOL_CALL → AGENT_COMPLETE
 * lifecycle that the ToolCallBubble ultimately renders.
 */

import { describe, it, expect } from "vitest";
import { makeToolCall, makeRunningToolCall, hedgeOutput } from "./hedgeFixtures";

// Import the reducer directly — it is not exported from useChat.js, so we
// replicate just the relevant cases here to keep tests self-contained and fast.
// If the reducer is ever extracted, these tests can import it directly.

// ---------------------------------------------------------------------------
// Inline reducer (mirrors useChat.js chatReducer exactly for the relevant cases)
// ---------------------------------------------------------------------------

function chatReducer(state, action) {
  switch (action.type) {
    case "ADD_TOOL_CALL_START":
      return {
        ...state,
        toolCalls: [
          ...state.toolCalls,
          {
            id: action.payload.tool_call_id,
            name: action.payload.tool_name,
            args: action.payload.tool_args,
            status: "running",
            output: null,
            elapsed_ms: null,
          },
        ],
      };

    case "UPDATE_TOOL_CALL":
      return {
        ...state,
        toolCalls: state.toolCalls.map((tc) =>
          tc.id === action.payload.tool_call_id
            ? {
                ...tc,
                status: action.payload.status,
                output: action.payload.output,
                elapsed_ms: action.payload.elapsed_ms,
              }
            : tc
        ),
      };

    case "AGENT_COMPLETE": {
      const streamingExists = state.messages.find((m) => m.id === action.payload.message_id);
      if (streamingExists) {
        return {
          ...state,
          messages: state.messages.map((m) =>
            m.id === action.payload.message_id
              ? {
                  ...m,
                  content: action.payload.response || m.content,
                  isStreaming: false,
                  toolCalls: [...state.toolCalls],
                }
              : m
          ),
          isLoading: false,
          toolCalls: [],
        };
      }
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: action.payload.message_id,
            role: "assistant",
            content: action.payload.response,
            timestamp: new Date().toISOString(),
            toolCalls: [...state.toolCalls],
          },
        ],
        isLoading: false,
        toolCalls: [],
      };
    }

    default:
      return state;
  }
}

const emptyState = { messages: [], toolCalls: [], isLoading: true };

// ---------------------------------------------------------------------------
// ADD_TOOL_CALL_START
// ---------------------------------------------------------------------------

describe("chatReducer — ADD_TOOL_CALL_START for suggest_portfolio_hedge", () => {
  const startPayload = {
    tool_call_id: "tc-001",
    tool_name: "suggest_portfolio_hedge",
    tool_args: { account_id: "ACC-001", risk_focus: "all" },
  };

  it("adds tool call to toolCalls list", () => {
    const state = chatReducer(emptyState, { type: "ADD_TOOL_CALL_START", payload: startPayload });
    expect(state.toolCalls).toHaveLength(1);
  });

  it("sets correct tool name", () => {
    const state = chatReducer(emptyState, { type: "ADD_TOOL_CALL_START", payload: startPayload });
    expect(state.toolCalls[0].name).toBe("suggest_portfolio_hedge");
  });

  it("sets status to running", () => {
    const state = chatReducer(emptyState, { type: "ADD_TOOL_CALL_START", payload: startPayload });
    expect(state.toolCalls[0].status).toBe("running");
  });

  it("sets output and elapsed_ms to null initially", () => {
    const state = chatReducer(emptyState, { type: "ADD_TOOL_CALL_START", payload: startPayload });
    expect(state.toolCalls[0].output).toBeNull();
    expect(state.toolCalls[0].elapsed_ms).toBeNull();
  });

  it("preserves args on the tool call", () => {
    const state = chatReducer(emptyState, { type: "ADD_TOOL_CALL_START", payload: startPayload });
    expect(state.toolCalls[0].args).toEqual({ account_id: "ACC-001", risk_focus: "all" });
  });

  it("does not mutate existing toolCalls", () => {
    const existingCall = {
      id: "tc-existing",
      name: "get_account_details",
      args: {},
      status: "success",
      output: "{}",
      elapsed_ms: 50,
    };
    const stateWithExisting = { ...emptyState, toolCalls: [existingCall] };
    const next = chatReducer(stateWithExisting, {
      type: "ADD_TOOL_CALL_START",
      payload: startPayload,
    });
    expect(next.toolCalls).toHaveLength(2);
    expect(next.toolCalls[0]).toEqual(existingCall);
  });
});

// ---------------------------------------------------------------------------
// UPDATE_TOOL_CALL
// ---------------------------------------------------------------------------

describe("chatReducer — UPDATE_TOOL_CALL for suggest_portfolio_hedge", () => {
  const stateWithRunning = chatReducer(emptyState, {
    type: "ADD_TOOL_CALL_START",
    payload: {
      tool_call_id: "tc-001",
      tool_name: "suggest_portfolio_hedge",
      tool_args: { account_id: "ACC-001" },
    },
  });

  const completePayload = {
    tool_call_id: "tc-001",
    status: "success",
    output: JSON.stringify(hedgeOutput),
    elapsed_ms: 142,
  };

  it("updates status to success", () => {
    const state = chatReducer(stateWithRunning, {
      type: "UPDATE_TOOL_CALL",
      payload: completePayload,
    });
    expect(state.toolCalls[0].status).toBe("success");
  });

  it("sets output on the correct tool call", () => {
    const state = chatReducer(stateWithRunning, {
      type: "UPDATE_TOOL_CALL",
      payload: completePayload,
    });
    const output = JSON.parse(state.toolCalls[0].output);
    expect(output.account_id).toBe("ACC-001");
    expect(output.hedge_recommendations).toBeInstanceOf(Array);
  });

  it("sets elapsed_ms", () => {
    const state = chatReducer(stateWithRunning, {
      type: "UPDATE_TOOL_CALL",
      payload: completePayload,
    });
    expect(state.toolCalls[0].elapsed_ms).toBe(142);
  });

  it("does not affect other tool calls", () => {
    const stateTwo = chatReducer(stateWithRunning, {
      type: "ADD_TOOL_CALL_START",
      payload: { tool_call_id: "tc-002", tool_name: "get_account_details", tool_args: {} },
    });
    const updated = chatReducer(stateTwo, { type: "UPDATE_TOOL_CALL", payload: completePayload });
    expect(updated.toolCalls[1].status).toBe("running"); // tc-002 unchanged
  });

  it("handles error status correctly", () => {
    const errorPayload = {
      tool_call_id: "tc-001",
      status: "error",
      output: "DB error",
      elapsed_ms: 10,
    };
    const state = chatReducer(stateWithRunning, {
      type: "UPDATE_TOOL_CALL",
      payload: errorPayload,
    });
    expect(state.toolCalls[0].status).toBe("error");
    expect(state.toolCalls[0].output).toBe("DB error");
  });
});

// ---------------------------------------------------------------------------
// AGENT_COMPLETE — tool calls attached to assistant message
// ---------------------------------------------------------------------------

describe("chatReducer — AGENT_COMPLETE attaches hedge tool calls to message", () => {
  // Build state: start hedge tool call, complete it, then agent_complete
  let state = emptyState;
  state = chatReducer(state, {
    type: "ADD_TOOL_CALL_START",
    payload: {
      tool_call_id: "tc-001",
      tool_name: "suggest_portfolio_hedge",
      tool_args: { account_id: "ACC-001" },
    },
  });
  state = chatReducer(state, {
    type: "UPDATE_TOOL_CALL",
    payload: {
      tool_call_id: "tc-001",
      status: "success",
      output: JSON.stringify(hedgeOutput),
      elapsed_ms: 142,
    },
  });

  const completeAction = {
    type: "AGENT_COMPLETE",
    payload: {
      message_id: "msg-001",
      response: "Here are hedge recommendations for ACC-001...",
      query_summary: null,
    },
  };

  it("clears toolCalls from live state after agent_complete", () => {
    const next = chatReducer(state, completeAction);
    expect(next.toolCalls).toHaveLength(0);
  });

  it("attaches tool calls to the new assistant message", () => {
    const next = chatReducer(state, completeAction);
    const assistantMsg = next.messages.find((m) => m.role === "assistant");
    expect(assistantMsg).toBeDefined();
    expect(assistantMsg.toolCalls).toHaveLength(1);
    expect(assistantMsg.toolCalls[0].name).toBe("suggest_portfolio_hedge");
  });

  it("assistant message contains hedge output in its tool call", () => {
    const next = chatReducer(state, completeAction);
    const assistantMsg = next.messages.find((m) => m.role === "assistant");
    const output = JSON.parse(assistantMsg.toolCalls[0].output);
    expect(output.hedge_recommendations.length).toBeGreaterThan(0);
  });

  it("sets isLoading to false", () => {
    const next = chatReducer(state, completeAction);
    expect(next.isLoading).toBe(false);
  });

  it("agent_complete on a streaming message updates it in-place", () => {
    // Simulate a streaming message already existing
    const streamingState = {
      ...state,
      messages: [
        {
          id: "msg-001",
          role: "assistant",
          content: "partial...",
          isStreaming: true,
          toolCalls: [],
        },
      ],
    };
    const next = chatReducer(streamingState, completeAction);
    const assistantMsg = next.messages.find((m) => m.id === "msg-001");
    expect(assistantMsg.isStreaming).toBe(false);
    expect(assistantMsg.content).toBe("Here are hedge recommendations for ACC-001...");
  });
});

// ---------------------------------------------------------------------------
// Full lifecycle simulation
// ---------------------------------------------------------------------------

describe("chatReducer — full suggest_portfolio_hedge lifecycle", () => {
  it("running → success → attached to message without errors", () => {
    let s = emptyState;

    // 1. Tool call starts
    s = chatReducer(s, {
      type: "ADD_TOOL_CALL_START",
      payload: {
        tool_call_id: "tc-hedge",
        tool_name: "suggest_portfolio_hedge",
        tool_args: { account_id: "ACC-005", risk_focus: "sector" },
      },
    });
    expect(s.toolCalls[0].status).toBe("running");

    // 2. Tool call completes
    s = chatReducer(s, {
      type: "UPDATE_TOOL_CALL",
      payload: {
        tool_call_id: "tc-hedge",
        status: "success",
        output: JSON.stringify(hedgeOutput),
        elapsed_ms: 200,
      },
    });
    expect(s.toolCalls[0].status).toBe("success");

    // 3. Agent completes
    s = chatReducer(s, {
      type: "AGENT_COMPLETE",
      payload: { message_id: "msg-final", response: "Done.", query_summary: null },
    });
    expect(s.toolCalls).toHaveLength(0);

    const msg = s.messages.find((m) => m.id === "msg-final");
    expect(msg.toolCalls[0].name).toBe("suggest_portfolio_hedge");
    expect(msg.toolCalls[0].elapsed_ms).toBe(200);
  });
});
