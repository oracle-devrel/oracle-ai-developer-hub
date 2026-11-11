import type { ResetResult } from "@oracle-mem0-ts-memory/shared";

import { assertOracleIdentifier } from "./config.js";
import { executeStatement } from "./pool.js";

export type ExecuteStatement = (sql: string) => Promise<void>;

function isMissingTable(error: unknown): boolean {
  return !!error && typeof error === "object" && "errorNum" in error && (error as { errorNum?: number }).errorNum === 942;
}

export async function resetDemoCollection(
  collectionName: string,
  execute: ExecuteStatement = executeStatement,
): Promise<ResetResult> {
  const name = assertOracleIdentifier(collectionName);
  if (!/^MEM0_[A-Z0-9_$#]*_DEMO$/.test(name)) {
    throw new Error("Reset is restricted to a configured MEM0 demo collection");
  }
  const targets = [name, assertOracleIdentifier(`${name}_ENTITY`)];
  const dropped: string[] = [];
  for (const target of targets) {
    try {
      await execute(`DROP TABLE ${target} PURGE`);
      dropped.push(target);
    } catch (error) {
      if (!isMissingTable(error)) throw error;
    }
  }
  return { collectionName: name, dropped };
}
