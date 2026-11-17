import type { JsonValue, OracleInspection, OraclePayloadSample } from "@oracle-mem0-ts-memory/shared";

import { assertOracleIdentifier } from "./config.js";
import { queryRows } from "./pool.js";

export type QueryRows = <T extends Record<string, unknown>>(sql: string, binds?: Record<string, unknown>) => Promise<T[]>;

function asObject(value: unknown): Record<string, unknown> {
  if (typeof value === "string") {
    try { return JSON.parse(value) as Record<string, unknown>; } catch { return {}; }
  }
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

const reserved = new Set(["data", "memory", "user_id", "userId", "id", "hash", "created_at", "updated_at", "api_key", "password", "token"]);

function safeSample(row: Record<string, unknown>): OraclePayloadSample {
  const payload = asObject(row.payload);
  const nested = asObject(payload.metadata);
  const metadata: Record<string, JsonValue> = {};
  for (const [key, value] of [...Object.entries(payload), ...Object.entries(nested)]) {
    if (reserved.has(key) || key === "metadata") continue;
    if (value === null || ["string", "number", "boolean"].includes(typeof value) || Array.isArray(value) || typeof value === "object") {
      metadata[key] = value as JsonValue;
    }
  }
  return {
    id: String(row.id ?? payload.id ?? ""),
    memory: typeof payload.data === "string" ? payload.data : typeof payload.memory === "string" ? payload.memory : undefined,
    userId: typeof payload.user_id === "string" ? payload.user_id : typeof payload.userId === "string" ? payload.userId : undefined,
    metadata,
  };
}

export async function inspectCollection(
  collectionName: string,
  query: QueryRows = queryRows,
): Promise<OracleInspection> {
  const name = assertOracleIdentifier(collectionName);
  const existence = await query<{ count: number }>(
    `SELECT COUNT(*) AS "count" FROM user_tables WHERE table_name = :name`,
    { name },
  );
  if (Number(existence[0]?.count || 0) === 0) {
    return { collectionName: name, exists: false, rowCount: 0, columns: [], vectorIndexes: [], samples: [] };
  }
  const [counts, columns, indexes, samples] = await Promise.all([
    query<{ row_count: number }>(`SELECT COUNT(*) AS "row_count" FROM ${name}`),
    query<{ name: string; data_type: string; nullable: string }>(
      `SELECT column_name AS "name", data_type AS "data_type", nullable AS "nullable" FROM user_tab_columns WHERE table_name = :name ORDER BY column_id`, { name },
    ),
    query<{ name: string; type: string; status: string }>(
      `SELECT index_name AS "name", index_type AS "type", status AS "status" FROM user_indexes WHERE table_name = :name AND index_type = 'VECTOR' ORDER BY index_name`, { name },
    ),
    query<Record<string, unknown>>(`SELECT id AS "id", payload AS "payload" FROM ${name} FETCH FIRST 5 ROWS ONLY`),
  ]);
  return {
    collectionName: name,
    exists: true,
    rowCount: Number(counts[0]?.row_count || 0),
    columns: columns.map((column) => ({ name: column.name, dataType: column.data_type, nullable: column.nullable === "Y" })),
    vectorIndexes: indexes.map((index) => ({ name: index.name, type: index.type, status: index.status })),
    samples: samples.map(safeSample),
  };
}
