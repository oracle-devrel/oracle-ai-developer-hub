export type JsonScalar = string | number | boolean | null;
export type JsonValue = JsonScalar | JsonValue[] | { [key: string]: JsonValue };

export interface UserScope {
  userId: string;
}

export interface MemoryRecord extends UserScope {
  id: string;
  memory: string;
  score?: number;
  metadata: Record<string, JsonValue>;
  createdAt?: string;
  updatedAt?: string;
}

export interface MemorySearchResponse {
  memories: MemoryRecord[];
  query?: string;
  userId: string;
}

export interface MemoryMutationResponse {
  memory?: MemoryRecord;
  events: MemoryRecord[];
  message: string;
}

export interface ChatRequest extends UserScope {
  message: string;
}

export interface ChatResponse extends UserScope {
  answer: string;
  retrievedMemories: MemoryRecord[];
  memoryEvents: MemoryRecord[];
}

export interface SetupState {
  mode: "demo" | "openai";
  oracleConfigured: boolean;
  openAIConfigured: boolean;
  missingVariables: string[];
  collectionName: string;
  embeddingModel: string;
  embeddingDimension: number;
  chatModel: string;
  createVectorIndex: boolean;
}

export interface AppStatus {
  api: "ok";
  setup: SetupState;
  database: { connected: boolean; detail: string };
}

export interface OracleColumn {
  name: string;
  dataType: string;
  nullable: boolean;
}

export interface OracleIndex {
  name: string;
  type: string;
  status: string;
}

export interface OraclePayloadSample {
  id: string;
  memory?: string;
  userId?: string;
  metadata: Record<string, JsonValue>;
}

export interface OracleInspection {
  collectionName: string;
  exists: boolean;
  rowCount: number;
  columns: OracleColumn[];
  vectorIndexes: OracleIndex[];
  samples: OraclePayloadSample[];
}

export interface ResetResult {
  collectionName: string;
  dropped: string[];
}
