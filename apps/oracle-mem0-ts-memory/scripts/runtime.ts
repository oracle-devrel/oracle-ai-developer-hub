import { resolve } from "node:path";
import { config as loadEnv } from "dotenv";
import { loadAppConfig } from "@oracle-mem0-ts-memory/db";

export function loadRuntimeConfig() {
  loadEnv({ path: resolve(process.cwd(), ".env"), quiet: true });
  return loadAppConfig();
}
