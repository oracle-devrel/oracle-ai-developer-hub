import { describe, expect, it, vi } from "vitest";

import type { MemoryRecord } from "@oracle-mem0-ts-memory/shared";

import { createChatService, createDemoAnswerPort, type AnswerPort } from "./chat-service.js";
import type { MemoryPort } from "./mem0-client.js";

const remembered: MemoryRecord = {
  id: "m1",
  memory: "Alice is vegetarian",
  userId: "alice",
  score: 0.91,
  metadata: { category: "food" },
};

function fakes(options: { search?: () => Promise<MemoryRecord[]>; answer?: () => Promise<string>; add?: () => Promise<MemoryRecord[]> } = {}) {
  const order: string[] = [];
  const memory: MemoryPort = {
    search: vi.fn(async () => { order.push("search"); return options.search ? options.search() : [remembered]; }),
    add: vi.fn(async () => { order.push("add"); return options.add ? options.add() : []; }),
    getAll: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  };
  const answer: AnswerPort = {
    complete: vi.fn(async () => { order.push("answer"); return options.answer ? options.answer() : "Try a vegetable curry."; }),
  };
  return { memory, answer, order };
}

describe("chat service", () => {
  it("answers from Oracle memories without running LLM inference in demo mode", async () => {
    const { memory } = fakes();
    const result = await createChatService(memory, createDemoAnswerPort(), { infer: false }).chat({ userId: "alice", message: "What food do I like?" });
    expect(result.answer).toContain("Alice is vegetarian");
    expect(result.memoryEvents).toEqual([]);
    expect(memory.add).not.toHaveBeenCalled();
  });

  it("does not invent preferences when no memories are found", async () => {
    const { memory } = fakes({ search: async () => [] });
    const result = await createChatService(memory, createDemoAnswerPort(), { infer: false }).chat({ userId: "alice", message: "What food do I like?" });
    expect(result.answer).toMatch(/no saved memories/i);
  });
  it("retrieves, answers, then ingests the completed turn", async () => {
    const { memory, answer, order } = fakes({ add: async () => [remembered] });
    const result = await createChatService(memory, answer).chat({ userId: "alice", message: "Dinner idea?" });
    expect(order).toEqual(["search", "answer", "add"]);
    expect(answer.complete).toHaveBeenCalledWith({ message: "Dinner idea?", memories: [remembered] });
    expect(memory.add).toHaveBeenCalledWith(
      [
        { role: "user", content: "Dinner idea?" },
        { role: "assistant", content: "Try a vegetable curry." },
      ],
      { userId: "alice", infer: true, metadata: { source: "chat" } },
    );
    expect(result).toMatchObject({ answer: "Try a vegetable curry.", retrievedMemories: [remembered], memoryEvents: [remembered] });
  });

  it("supports an answer when no memories are retrieved", async () => {
    const { memory, answer } = fakes({ search: async () => [] });
    await createChatService(memory, answer).chat({ userId: "alice", message: "Hello" });
    expect(answer.complete).toHaveBeenCalledWith({ message: "Hello", memories: [] });
  });

  it("rejects blank input before providers run", async () => {
    const { memory, answer } = fakes();
    await expect(createChatService(memory, answer).chat({ userId: " ", message: "Hello" })).rejects.toThrow(/user id/i);
    expect(memory.search).not.toHaveBeenCalled();
  });

  it.each([
    ["retrieval", { search: async () => { throw new Error("vector unavailable"); } }],
    ["generation", { answer: async () => { throw new Error("model unavailable"); } }],
    ["ingestion", { add: async () => { throw new Error("write unavailable"); } }],
  ] as const)("labels %s provider failures", async (phase, options) => {
    const { memory, answer } = fakes(options);
    await expect(createChatService(memory, answer).chat({ userId: "alice", message: "Hello" })).rejects.toMatchObject({ phase });
    if (phase === "generation") expect(memory.add).not.toHaveBeenCalled();
  });
});
