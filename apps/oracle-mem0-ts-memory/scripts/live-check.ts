import { createAppServices } from "@oracle-mem0-ts-memory/core";
import { checkOracleConnection } from "@oracle-mem0-ts-memory/db";
import { loadRuntimeConfig } from "./runtime.js";

const config = loadRuntimeConfig();
const services = createAppServices(config);
const userId = `live-check-${Date.now()}`;
let created: Awaited<ReturnType<typeof services.memoryService.create>> = [];
try {
  console.log(await checkOracleConnection());
  created = await services.memoryService.create(userId, "The live-check preference is jasmine tea.", { source: "live-check" });
  if (created.length !== 1) throw new Error("Live create did not return exactly one memory event");
  await services.memoryService.update(userId, created[0]!.id, "The live-check preference is jasmine green tea.");
  const found = await services.memoryService.search(userId, "What tea is preferred?", 5);
  if (!found.some((item) => item.memory.toLowerCase().includes("jasmine green"))) throw new Error("Live semantic search did not retrieve the updated memory");
  console.log(`Live memory round-trip OK (${found.length} result${found.length === 1 ? "" : "s"}).`);
} catch (error) {
  const detail = error && typeof error === "object" && "status" in error && error.status === 429
    ? "OpenAI rejected the request because the configured account has no remaining API credits."
    : error instanceof Error ? error.message : "Unknown live-check failure";
  console.error(`Live memory round-trip failed: ${detail}`);
  process.exitCode = 1;
} finally {
  for (const item of created) await services.memoryService.remove(userId, item.id);
  if ((await services.memoryService.list(userId)).length !== 0) throw new Error("Live-check cleanup left test memories behind");
}
process.exit(process.exitCode ?? 0);
