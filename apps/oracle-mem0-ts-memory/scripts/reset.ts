import { createInterface } from "node:readline/promises";

import { resetDemoCollection } from "@oracle-mem0-ts-memory/db";
import { loadRuntimeConfig } from "./runtime.js";
import { canResetWithoutPrompt } from "./reset-policy.js";

const config = loadRuntimeConfig();
if (!canResetWithoutPrompt(process.argv, !!process.stdin.isTTY)) {
  if (!process.stdin.isTTY) throw new Error("Reset requires --yes when no interactive terminal is attached");
  const prompt = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await prompt.question(`Type ${config.collectionName} to confirm dropping this demo collection: `);
  prompt.close();
  if (answer !== config.collectionName) throw new Error("Reset cancelled: collection name did not match");
}
const result = await resetDemoCollection(config.collectionName);
console.log(result.dropped.length ? `Dropped: ${result.dropped.join(", ")}` : "Demo collection was already absent.");
process.exit(0);
