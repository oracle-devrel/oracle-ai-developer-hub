import type { MemoryService } from "./memory-service.js";
import { DEMO_MEMORIES } from "@oracle-mem0-ts-memory/samples";

export { DEMO_MEMORIES } from "@oracle-mem0-ts-memory/samples";

export async function seedDemoMemories(memoryService: Pick<MemoryService, "create" | "list">): Promise<{ added: number }> {
  const existingByUser = new Map<string, Set<string>>();
  for (const userId of new Set(DEMO_MEMORIES.map((item) => item.userId))) {
    const memories = await memoryService.list(userId, 100);
    existingByUser.set(userId, new Set(memories.map((item) => item.memory.trim())));
  }

  let added = 0;
  for (const item of DEMO_MEMORIES) {
    if (existingByUser.get(item.userId)?.has(item.text)) continue;
    await memoryService.create(item.userId, item.text, { source: "seed", demo: true, category: item.category });
    existingByUser.get(item.userId)?.add(item.text);
    added += 1;
  }
  return { added };
}
