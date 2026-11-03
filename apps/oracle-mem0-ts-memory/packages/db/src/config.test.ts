import { describe, expect, it } from "vitest";

import { assertOracleIdentifier, loadAppConfig } from "./config.js";

const validEnv = {
  ORACLE_USER: "memory_user",
  ORACLE_PASSWORD: "secret",
  ORACLE_CONNECT_STRING: "localhost:1521/FREEPDB1",
  OPENAI_API_KEY: "test-key",
};

describe("loadAppConfig", () => {
  it("reports missing variable names without secret values", () => {
    expect(() => loadAppConfig({ ORACLE_PASSWORD: "do-not-print" })).toThrow(
      /ORACLE_USER, ORACLE_CONNECT_STRING/,
    );
    expect(() => loadAppConfig({ ORACLE_PASSWORD: "do-not-print" })).not.toThrow(
      /do-not-print/,
    );
  });

  it("uses safe application defaults", () => {
    expect(loadAppConfig(validEnv)).toMatchObject({
      mode: "demo",
      collectionName: "MEM0_TS_LOCAL_DEMO",
      createVectorIndex: false,
      embeddingDimension: 24,
      port: 8787,
    });
  });

  it("starts without an OpenAI key and keeps the demo collection separate", () => {
    const { OPENAI_API_KEY: _, ...env } = validEnv;
    expect(loadAppConfig({ ...env, MEM0_COLLECTION_NAME: "MEM0_TS_MEMORY_DEMO" })).toMatchObject({
      mode: "demo", collectionName: "MEM0_TS_LOCAL_DEMO", openAI: { apiKey: "" },
    });
  });

  it("requires a key only when OpenAI mode is explicitly selected", () => {
    const { OPENAI_API_KEY: _, ...env } = validEnv;
    expect(() => loadAppConfig({ ...env, MEM0_MODE: "openai" })).toThrow(/OPENAI_API_KEY/);
    expect(loadAppConfig({ ...validEnv, MEM0_MODE: "openai" })).toMatchObject({
      mode: "openai", collectionName: "MEM0_TS_MEMORY_DEMO", embeddingDimension: 1536,
    });
  });

  it("rejects unsupported modes", () => {
    expect(() => loadAppConfig({ ...validEnv, MEM0_MODE: "unknown" })).toThrow(/MEM0_MODE/);
  });

  it("accepts ORACLE_DSN as a compatibility alias", () => {
    const { ORACLE_CONNECT_STRING: _, ...env } = validEnv;
    expect(loadAppConfig({ ...env, ORACLE_DSN: "localhost:1521/FREEPDB1" }).oracle.connectString).toBe(
      "localhost:1521/FREEPDB1",
    );
  });
});

describe("assertOracleIdentifier", () => {
  it("accepts an uppercase demo identifier", () => {
    expect(assertOracleIdentifier("MEM0_TS_MEMORY_DEMO")).toBe("MEM0_TS_MEMORY_DEMO");
  });

  it.each(["", "mem0-demo", '"X";DROP TABLE Y', "A".repeat(31)])(
    "rejects unsafe identifier %j",
    (value) => expect(() => assertOracleIdentifier(value)).toThrow(),
  );
});
