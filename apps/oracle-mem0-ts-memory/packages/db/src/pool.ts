import oracledb, { type Pool } from "oracledb";

import { loadAppConfig, type AppConfig } from "./config.js";

let poolPromise: Promise<Pool> | undefined;

export async function getOraclePool(config: AppConfig = loadAppConfig()): Promise<Pool> {
  poolPromise ??= oracledb.createPool({
    ...config.oracle,
    poolMin: 1,
    poolMax: 4,
    poolIncrement: 1,
  });
  return poolPromise;
}

export async function closeOraclePool(): Promise<void> {
  if (!poolPromise) return;
  const pool = await poolPromise;
  poolPromise = undefined;
  await pool.close(5);
}

export async function queryRows<T extends Record<string, unknown>>(
  sql: string,
  binds: Record<string, unknown> = {},
): Promise<T[]> {
  const pool = await getOraclePool();
  const connection = await pool.getConnection();
  try {
    const result = await connection.execute<T>(sql, binds as oracledb.BindParameters, { outFormat: oracledb.OUT_FORMAT_OBJECT });
    return (result.rows || []) as T[];
  } finally {
    await connection.close();
  }
}

export async function executeStatement(sql: string): Promise<void> {
  const pool = await getOraclePool();
  const connection = await pool.getConnection();
  try {
    await connection.execute(sql);
    await connection.commit();
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    await connection.close();
  }
}

export async function checkOracleConnection(): Promise<string> {
  const rows = await queryRows<{ version: string; service_name: string }>(
    `SELECT version_full AS "version", sys_context('USERENV', 'SERVICE_NAME') AS "service_name" FROM product_component_version WHERE product LIKE 'Oracle Database%' FETCH FIRST 1 ROW ONLY`,
  );
  const row = rows[0];
  return row ? `Oracle ${row.version} (${row.service_name})` : "Oracle connection ready";
}
