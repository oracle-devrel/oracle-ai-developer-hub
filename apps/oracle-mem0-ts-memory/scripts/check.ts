import { checkOracleConnection } from "@oracle-mem0-ts-memory/db";
import { loadRuntimeConfig } from "./runtime.js";

const config = loadRuntimeConfig();
console.log(`Configuration OK: ${config.collectionName}, ${config.embeddingDimension} dimensions`);
console.log(await checkOracleConnection());
process.exit(0);
