import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import dotenv from "dotenv";
import oracledb from "oracledb";
import { Embeddings } from "@langchain/core/embeddings";
import { Document } from "@langchain/core/documents";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { ChatOpenAI } from "@langchain/openai";
import {
  DistanceStrategy,
  OracleVS,
  VectorElementFormat,
  createIndex,
  dropTablePurge,
} from "@oracle/langchain-oracledb";

// -----------------------------------------------------------------------------
// Configuration
// -----------------------------------------------------------------------------

dotenv.config({ path: path.resolve(process.cwd(), ".env"), quiet: true });

if (oracledb.defaults) {
  oracledb.defaults.program = "devrel-developerhub-langchain-js-oracle-rag";
}

const tableName = (process.env.LANGCHAIN_JS_TABLE || "LC_JS_RAG_DEMO").toUpperCase();
const createVectorIndex =
  (process.env.LANGCHAIN_JS_CREATE_INDEX || "false").toLowerCase() === "true";
const resultsPath = path.resolve(process.cwd(), "rag_results.json");

const dbUser = process.env.DB_USER || process.env.ORACLEDB_USER;
const dbPassword = process.env.DB_PASSWORD || process.env.ORACLEDB_PASSWORD;
const dbConnectString =
  process.env.DB_CONNECT_STRING ||
  process.env.DB_DSN ||
  process.env.ORACLEDB_CONNECTION_STRING;

const llmApiKey = process.env.OPENAI_API_KEY || process.env.MODEL_PROVIDER_API_KEY;
const llmModel =
  process.env.LANGCHAIN_JS_LLM_MODEL ||
  process.env.OPENAI_MODEL ||
  process.env.OAMP_LLM_MODEL ||
  "gpt-4o-mini";

const missing = [
  ["DB_USER", dbUser],
  ["DB_PASSWORD", dbPassword],
  ["DB_CONNECT_STRING or DB_DSN", dbConnectString],
]
  .filter(([, value]) => !value)
  .map(([name]) => name);

if (missing.length > 0) {
  throw new Error(`Missing required environment variables: ${missing.join(", ")}`);
}

function writeResults(payload) {
  fs.writeFileSync(resultsPath, JSON.stringify(payload, null, 2));
}

async function createPool() {
  return oracledb.createPool({
    user: dbUser,
    password: dbPassword,
    connectString: dbConnectString,
  });
}

// -----------------------------------------------------------------------------
// Demo embeddings
// -----------------------------------------------------------------------------

class DemoEmbeddings extends Embeddings {
  constructor() {
    super({});
    this.dimensions = 12;
    this.terms = [
      "oracle",
      "database",
      "vector",
      "langchain",
      "javascript",
      "typescript",
      "rag",
      "metadata",
      "freesql",
      "agent",
      "retrieval",
      "enterprise",
    ];
  }

  textToVector(text) {
    const lower = text.toLowerCase();
    const vector = this.terms.map((term) => {
      const matches = lower.match(new RegExp(term, "g"));
      return matches ? matches.length : 0;
    });

    for (const token of lower.split(/[^a-z0-9]+/).filter(Boolean)) {
      let bucket = 0;
      for (const char of token) {
        bucket = (bucket + char.charCodeAt(0)) % this.dimensions;
      }
      vector[bucket] += 0.15;
    }

    const norm =
      Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
    return vector.map((value) => Number((value / norm).toFixed(6)));
  }

  async embedQuery(text) {
    return this.textToVector(text);
  }

  async embedDocuments(texts) {
    return texts.map((text) => this.textToVector(text));
  }
}

// -----------------------------------------------------------------------------
// Demo corpus and answer generation
// -----------------------------------------------------------------------------

function docsForDemo() {
  return [
    new Document({
      pageContent:
        "Oracle AI Database stores vectors alongside operational data, so RAG applications can keep retrieval close to governed enterprise records.",
      metadata: {
        source: "oracle-ai-database",
        category: "database",
        product: "Oracle AI Database",
        priority: "high",
        audience: "architect",
      },
    }),
    new Document({
      pageContent:
        "LangChain.js RAG applications use OracleVS with Oracle AI Database as a vector store for adding documents, preserving metadata, and running similarity search retrieval.",
      metadata: {
        source: "langchain-js",
        category: "framework",
        product: "LangChain.js",
        priority: "high",
        audience: "developer",
      },
    }),
    new Document({
      pageContent:
        "FreeSQL gives developers a hosted Oracle Database schema for tutorials that only need normal schema table operations.",
      metadata: {
        source: "freesql",
        category: "setup",
        product: "FreeSQL",
        priority: "medium",
        audience: "developer",
      },
    }),
    new Document({
      pageContent:
        "Metadata filters narrow OracleVS retrieval by product, source, category, tenant, priority, or other JSON metadata fields.",
      metadata: {
        source: "metadata-filtering",
        category: "retrieval",
        product: "OracleVS",
        priority: "high",
        audience: "developer",
      },
    }),
    new Document({
      pageContent:
        "Maximal marginal relevance helps LangChain.js retrieve a diverse context set instead of returning several near-duplicate chunks.",
      metadata: {
        source: "mmr",
        category: "retrieval",
        product: "LangChain.js",
        priority: "medium",
        audience: "developer",
      },
    }),
    new Document({
      pageContent:
        "A production RAG service can swap the demo embedding class for OpenAI, OCI Generative AI, or Oracle-backed embeddings without changing OracleVS retrieval code.",
      metadata: {
        source: "embedding-provider",
        category: "architecture",
        product: "LangChain.js",
        priority: "medium",
        audience: "architect",
      },
    }),
    new Document({
      pageContent:
        "Autonomous AI Database and local Oracle Database use the same node-oracledb connection pattern when the schema can create and manage application tables.",
      metadata: {
        source: "connection-options",
        category: "setup",
        product: "node-oracledb",
        priority: "medium",
        audience: "developer",
      },
    }),
  ];
}

function docRow(doc, distance, rank) {
  return {
    rank,
    distance: distance === undefined ? null : Number(distance.toFixed(6)),
    source: doc.metadata.source,
    product: doc.metadata.product,
    category: doc.metadata.category,
    snippet: doc.pageContent,
  };
}

function buildContext(rows) {
  return rows
    .map(
      (row) =>
        `[${row.rank}] source=${row.source}; product=${row.product}; category=${row.category}; snippet=${row.snippet}`,
    )
    .join("\n");
}

function contentToText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") return part;
        if (part && typeof part === "object" && "text" in part) return part.text;
        return JSON.stringify(part);
      })
      .join("");
  }
  return String(content ?? "");
}

async function buildAnswer(question, rows) {
  if (!llmApiKey) {
    return [
      "Grounded-answer generation was skipped because no OPENAI_API_KEY was set.",
      "The OracleVS retrieval steps still completed successfully.",
      "",
      "Retrieved context:",
      buildContext(rows),
    ].join("\n");
  }

  const model = new ChatOpenAI({
    apiKey: llmApiKey,
    model: llmModel,
    temperature: 0,
  });

  const response = await model.invoke([
    new SystemMessage(
      "You are a concise technical assistant. Answer only from the retrieved context. If the context is insufficient, say what is missing.",
    ),
    new HumanMessage(
      `Question:\n${question}\n\nRetrieved context:\n${buildContext(rows)}\n\nWrite a grounded answer in 3-5 sentences and mention the Oracle/LangChain components that support the answer.`,
    ),
  ]);

  return contentToText(response.content).trim();
}

// -----------------------------------------------------------------------------
// Database helpers
// -----------------------------------------------------------------------------

async function tableExists(connection, name) {
  const result = await connection.execute(
    `SELECT COUNT(*) FROM user_tables WHERE table_name = :name`,
    [name.toUpperCase()],
  );
  return Number(result.rows[0][0]) > 0;
}

async function runTablePreflight(connection, summary) {
  const diagTable = "LC_JS_PREFLIGHT";

  try {
    await connection.execute(`DROP TABLE ${diagTable} PURGE`);
  } catch (error) {
    if (!String(error.message).includes("ORA-00942")) throw error;
  }

  await connection.execute(
    `CREATE TABLE ${diagTable} (id NUMBER PRIMARY KEY, note VARCHAR2(100))`,
  );
  await connection.execute(
    `INSERT INTO ${diagTable} VALUES (1, 'table permission check')`,
    [],
    { autoCommit: true },
  );
  const rows = await connection.execute(`SELECT COUNT(*) FROM ${diagTable}`);
  await connection.execute(`DROP TABLE ${diagTable} PURGE`);

  summary.push({
    step: "table_operations",
    status: "PASS",
    detail: `Created, inserted, selected ${rows.rows[0][0]} row, and dropped a test table`,
  });
}

async function checkTablespaceQuota(connection) {
  const defaultTablespaceResult = await connection.execute(
    `SELECT default_tablespace
     FROM user_users`,
  );
  const defaultTablespace = defaultTablespaceResult.rows?.[0]?.[0];

  if (!defaultTablespace) {
    return {
      status: "UNKNOWN",
      detail: "Could not determine the schema default tablespace",
    };
  }

  const result = await connection.execute(
    `SELECT tablespace_name, bytes, max_bytes
     FROM user_ts_quotas
     WHERE tablespace_name = :defaultTablespace`,
    [defaultTablespace],
  );

  if (!result.rows || result.rows.length === 0) {
    return {
      status: "UNKNOWN",
      detail: `No quota row returned for default tablespace ${defaultTablespace}`,
    };
  }

  const [tablespaceName, usedBytes, maxBytes] = result.rows[0];

  if (Number(maxBytes) < 0) {
    return { status: "PASS", detail: `${tablespaceName}: unlimited quota` };
  }

  const freeBytes = Number(maxBytes) - Number(usedBytes);
  const usedMb = Number(usedBytes) / 1024 / 1024;
  const maxMb = Number(maxBytes) / 1024 / 1024;
  const freeMb = freeBytes / 1024 / 1024;

  if (freeBytes < 2_500_000) {
    return {
      status: "MISSING",
      detail: `${tablespaceName}: ${usedMb.toFixed(2)} MB used of ${maxMb.toFixed(2)} MB; only ${freeMb.toFixed(2)} MB remains.`,
    };
  }

  return {
    status: "PASS",
    detail: `${tablespaceName}: ${usedMb.toFixed(2)} MB used of ${maxMb.toFixed(2)} MB; ${freeMb.toFixed(2)} MB remains`,
  };
}

async function inspectVectorTable(connection, name) {
  const tableCount = await connection.execute(`SELECT COUNT(*) FROM ${name}`);
  const columnRows = await connection.execute(
    `SELECT column_name, data_type
     FROM user_tab_columns
     WHERE table_name = :tableName
     ORDER BY column_id`,
    [name],
  );
  const indexRows = await connection.execute(
    `SELECT index_name, index_type
     FROM user_indexes
     WHERE table_name = :tableName
     ORDER BY index_name`,
    [name],
  );

  return {
    rowCount: Number(tableCount.rows[0][0]),
    columns: columnRows.rows.map(([column, type]) => ({ column, type })),
    indexes: indexRows.rows.map(([index, type]) => {
      const indexName = String(index);
      const indexType = String(type);
      const isVectorIndex =
        indexName.endsWith("_HNSW_IDX") ||
        indexName.endsWith("_IVF_IDX") ||
        indexType.toUpperCase().includes("VECTOR");

      return {
        index: indexName,
        type: indexType,
        category: isVectorIndex ? "vector" : "internal/system",
      };
    }),
  };
}

// -----------------------------------------------------------------------------
// OracleVS + retrieval
// -----------------------------------------------------------------------------

async function prepareVectorStore(pool, connection, summary) {
  await runTablePreflight(connection, summary);

  if (await tableExists(connection, tableName)) {
    await dropTablePurge(connection, tableName);
    summary.push({
      step: "reset_vector_store",
      status: "PASS",
      detail: `Dropped existing ${tableName}`,
    });
  } else {
    summary.push({
      step: "reset_vector_store",
      status: "PASS",
      detail: `${tableName} did not exist before this run`,
    });
  }

  const quotaCheck = await checkTablespaceQuota(connection);
  summary.push({
    step: "tablespace_quota",
    status: quotaCheck.status,
    detail: quotaCheck.detail,
  });

  if (quotaCheck.status === "MISSING") {
    throw new Error(quotaCheck.detail);
  }

  const embeddings = new DemoEmbeddings();
  const documents = docsForDemo();

  const vectorStore = await OracleVS.fromDocuments(documents, embeddings, {
    client: pool,
    tableName,
    query: "Oracle AI Database LangChain.js RAG",
    distanceStrategy: DistanceStrategy.COSINE,
    format: VectorElementFormat.FLOAT32,
    description: "LangChain.js RAG demo table for Oracle AI Database",
  });

  summary.push({
    step: "oraclevs_ingest",
    status: "PASS",
    detail: `Inserted ${documents.length} documents into ${tableName}`,
  });

  if (createVectorIndex) {
    try {
      const vectorIndexName = `${tableName}_HNSW_IDX`;
      await createIndex(connection, vectorStore, {
        idxName: vectorIndexName,
        idxType: "HNSW",
        accuracy: 90,
        parallel: 1,
      });
      summary.push({
        step: "vector_index",
        status: "PASS",
        detail: `Created or reused ${vectorIndexName}`,
      });
    } catch (error) {
      summary.push({
        step: "vector_index",
        status: "OPTIONAL",
        detail: `Vector index skipped: ${String(error.message || error)
          .split("\n")[0]
          .slice(0, 160)}`,
      });
    }
  } else {
    summary.push({
      step: "vector_index",
      status: "READY",
      detail:
        "Set LANGCHAIN_JS_CREATE_INDEX=true to create an HNSW vector index when supported",
    });
  }

  return { vectorStore, documents };
}

async function runRetrievalExamples(vectorStore, summary) {
  const question =
    "How can a JavaScript RAG application use OracleVS with Oracle AI Database as a vector store for retrieval?";

  const rawResults = await vectorStore.similaritySearchWithScore(question, 4);
  const searchResults = rawResults.map(([doc, score], index) =>
    docRow(doc, score, index + 1),
  );
  summary.push({
    step: "similarity_search",
    status: "PASS",
    detail: `Retrieved ${searchResults.length} documents`,
  });

  const filteredRawResults = await vectorStore.similaritySearchWithScore(
    "How do metadata filters improve retrieval?",
    3,
    { category: { "$eq": "retrieval" } },
  );
  const filteredResults = filteredRawResults.map(([doc, score], index) =>
    docRow(doc, score, index + 1),
  );
  summary.push({
    step: "metadata_filter",
    status: "PASS",
    detail: `Retrieved ${filteredResults.length} retrieval-category documents`,
  });

  const mmrDocs = await vectorStore.maxMarginalRelevanceSearch(
    "What does the JavaScript integration provide for RAG?",
    { k: 3, fetchK: 5, lambda: 0.5 },
  );
  const mmrResults = mmrDocs.map((doc, index) =>
    docRow(doc, undefined, index + 1),
  );
  summary.push({
    step: "mmr_retrieval",
    status: "PASS",
    detail: `Selected ${mmrResults.length} diverse documents`,
  });

  const ragAnswer = await buildAnswer(question, searchResults);
  summary.push({
    step: "rag_generation",
    status: llmApiKey ? "PASS" : "SKIPPED",
    detail: llmApiKey
      ? `Generated a grounded answer with ${llmModel}`
      : "Set OPENAI_API_KEY to run the final grounded-answer generation step",
  });

  return {
    question,
    searchResults,
    filteredResults,
    mmrResults,
    ragAnswer,
  };
}

// -----------------------------------------------------------------------------
// End-to-end runner
// -----------------------------------------------------------------------------

async function run() {
  const summary = [];
  let pool;
  let connection;

  try {
    pool = await createPool();
    connection = await pool.getConnection();
    summary.push({
      step: "connect",
      status: "PASS",
      detail: "Connected with node-oracledb",
    });

    const { vectorStore, documents } = await prepareVectorStore(
      pool,
      connection,
      summary,
    );
    const retrieval = await runRetrievalExamples(vectorStore, summary);
    const tableInspection = await inspectVectorTable(connection, tableName);

    const payload = {
      tableName,
      summary,
      tableInspection,
      corpus: docsForDemo().map((doc, index) => ({
        id: index + 1,
        pageContent: doc.pageContent,
        metadata: doc.metadata,
      })),
      ...retrieval,
    };

    writeResults(payload);

    console.log(
      `Workflow completed: ${documents.length} documents ingested into ${tableName}; ` +
        `${retrieval.searchResults.length} similarity results, ` +
        `${retrieval.filteredResults.length} filtered results, ` +
        `${retrieval.mmrResults.length} MMR results.`,
    );
  } finally {
    if (connection) await connection.close();
    if (pool) await pool.close(0);
  }
}

run().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
