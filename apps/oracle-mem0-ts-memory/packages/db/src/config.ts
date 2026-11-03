export interface AppConfig {
  mode: "demo" | "openai";
  oracle: { user: string; password: string; connectString: string };
  openAI: { apiKey: string; chatModel: string; embeddingModel: string };
  collectionName: string;
  embeddingDimension: number;
  createVectorIndex: boolean;
  port: number;
}

export function assertOracleIdentifier(value: string): string {
  if (!/^[A-Z][A-Z0-9_$#]{0,29}$/.test(value)) {
    throw new Error("Oracle identifiers must be 1-30 uppercase alphanumeric characters and may include _, $, or #");
  }
  return value;
}

function required(env: NodeJS.ProcessEnv | Record<string, string | undefined>, names: string[]): string[] {
  return names.filter((name) => !env[name]?.trim());
}

function parseBoolean(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

export function loadAppConfig(env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env): AppConfig {
  const mode = env.MEM0_MODE?.trim().toLowerCase() || "demo";
  if (mode !== "demo" && mode !== "openai") throw new Error("MEM0_MODE must be demo or openai");
  const connectString = env.ORACLE_CONNECT_STRING?.trim() || env.ORACLE_DSN?.trim();
  const normalized = { ...env, ORACLE_CONNECT_STRING: connectString };
  const missing = required(normalized, [
    "ORACLE_USER",
    "ORACLE_PASSWORD",
    "ORACLE_CONNECT_STRING",
    ...(mode === "openai" ? ["OPENAI_API_KEY"] : []),
  ]);
  if (missing.length) throw new Error(`Missing required environment variables: ${missing.join(", ")}`);

  const collectionName = assertOracleIdentifier(mode === "demo"
    ? env.MEM0_DEMO_COLLECTION_NAME?.trim() || "MEM0_TS_LOCAL_DEMO"
    : env.MEM0_COLLECTION_NAME?.trim() || "MEM0_TS_MEMORY_DEMO");
  const embeddingDimension = mode === "demo" ? 24 : Number(env.OPENAI_EMBEDDING_DIMENSION || 1536);
  if (!Number.isInteger(embeddingDimension) || embeddingDimension < 1) {
    throw new Error("OPENAI_EMBEDDING_DIMENSION must be a positive integer");
  }
  const port = Number(env.PORT || 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("PORT must be between 1 and 65535");

  return {
    mode,
    oracle: {
      user: env.ORACLE_USER!.trim(),
      password: env.ORACLE_PASSWORD!,
      connectString: connectString!,
    },
    openAI: {
      apiKey: env.OPENAI_API_KEY?.trim() || "",
      chatModel: env.OPENAI_MODEL?.trim() || "gpt-4o-mini",
      embeddingModel: env.OPENAI_EMBEDDING_MODEL?.trim() || "text-embedding-3-small",
    },
    collectionName,
    embeddingDimension,
    createVectorIndex: parseBoolean(env.MEM0_CREATE_VECTOR_INDEX, false),
    port,
  };
}
