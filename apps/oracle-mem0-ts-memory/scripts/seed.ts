import { createAppServices, seedDemoMemories } from "@oracle-mem0-ts-memory/core";
import { loadRuntimeConfig } from "./runtime.js";

const services = createAppServices(loadRuntimeConfig());
const result = await seedDemoMemories(services.memoryService);
console.log(`Seeded ${result.added} demo memories.`);
process.exit(0);
