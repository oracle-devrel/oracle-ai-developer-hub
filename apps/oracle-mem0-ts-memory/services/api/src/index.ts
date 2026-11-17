import { resolve } from "node:path";

import { serve } from "@hono/node-server";
import { serveStatic } from "@hono/node-server/serve-static";
import { config as loadEnv } from "dotenv";

import { createAppServices, seedDemoMemories } from "@oracle-mem0-ts-memory/core";
import { checkOracleConnection, inspectCollection, loadAppConfig, resetDemoCollection } from "@oracle-mem0-ts-memory/db";

import { createApp } from "./app.js";
import { createResettableServices } from "./service-runtime.js";

const appRoot = process.env.INIT_CWD || process.cwd();
loadEnv({ path: resolve(appRoot, ".env"), quiet: true });
const config = loadAppConfig();
const services = createResettableServices(() => createAppServices(config));

const app = createApp({
  setup: {
    mode: config.mode,
    oracleConfigured: true,
    openAIConfigured: Boolean(config.openAI.apiKey),
    missingVariables: [],
    collectionName: config.collectionName,
    embeddingModel: config.mode === "demo" ? "deterministic-demo" : config.openAI.embeddingModel,
    embeddingDimension: config.embeddingDimension,
    chatModel: config.mode === "demo" ? "none" : config.openAI.chatModel,
    createVectorIndex: config.createVectorIndex,
  },
  checkDatabase: checkOracleConnection,
  chat: (request) => services.current().chatService.chat(request),
  listMemories: (userId, limit) => services.current().memoryService.list(userId, limit),
  searchMemories: (userId, query, limit) => services.current().memoryService.search(userId, query, limit),
  createMemory: (userId, text, metadata) => services.current().memoryService.create(userId, text, metadata),
  updateMemory: (userId, id, text) => services.current().memoryService.update(userId, id, text),
  deleteMemory: (userId, id) => services.current().memoryService.remove(userId, id),
  inspect: () => inspectCollection(config.collectionName),
  seed: () => seedDemoMemories(services.current().memoryService),
  reset: () => services.reset(() => resetDemoCollection(config.collectionName)),
});

const webDist = process.env.WEB_DIST_DIR || resolve(appRoot, "apps/web/dist");
app.use("/*", serveStatic({ root: webDist }));
app.get("*", serveStatic({ path: resolve(webDist, "index.html") }));

serve({ fetch: app.fetch, port: config.port }, ({ port }) => {
  console.log(`Oracle Mem0 API listening on http://localhost:${port}`);
});
