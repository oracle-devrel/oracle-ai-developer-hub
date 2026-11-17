import type { AppConfig } from "@oracle-mem0-ts-memory/db";

import { createChatService, createDemoAnswerPort, createOpenAIAnswerPort } from "./chat-service.js";
import { createMem0Port } from "./mem0-client.js";
import { createMemoryService } from "./memory-service.js";

export function createAppServices(config: AppConfig) {
  const memoryPort = createMem0Port(config);
  return {
    memoryPort,
    memoryService: createMemoryService(memoryPort),
    chatService: config.mode === "demo"
      ? createChatService(memoryPort, createDemoAnswerPort(), { infer: false })
      : createChatService(memoryPort, createOpenAIAnswerPort(config)),
  };
}
