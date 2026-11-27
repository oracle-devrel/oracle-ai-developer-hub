import "dotenv/config";
import { readFile, readdir } from "node:fs/promises";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const SAMPLES_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "samples");
const CONCURRENCY = 4;
// The sample folders are the labels. The first few PDFs of each folder are uploaded with their type so the
// database holds labeled examples; every other PDF is then classified by k-NN against those examples.
const LABELED_PER_TYPE = 5;
const TYPE_BY_DIR: Record<string, string> = {
  invoices: "invoice",
  "purchase-orders": "purchase_order",
  "delivery-notes": "delivery_note",
};
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 120_000;

interface DocResult {
  id: string;
  status: string;
  docType: string;
  failedReason: string | null;
  filename: string;
  durationMs: number;
}

async function uploadAndWait(filePath: string, base: string, docType?: string): Promise<DocResult> {
  const start = Date.now();
  const bytes = await readFile(filePath);
  const filename = filePath.split("/").pop()!;
  const form = new FormData();
  form.append("file", new Blob([bytes], { type: "application/pdf" }), filename);

  const query = docType ? `?docType=${encodeURIComponent(docType)}` : "";
  const res = await fetch(`${base}/documents${query}`, { method: "POST", body: form });
  if (!res.ok) {
    throw new Error(`upload failed (${res.status}): ${await res.text()}`);
  }
  const created = (await res.json()) as { id: string };

  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const poll = await fetch(`${base}/documents/${created.id}`);
    const doc = (await poll.json()) as {
      id: string;
      status: string;
      docType: string;
      failedReason: string | null;
    };
    if (doc.status === "done" || doc.status === "failed") {
      return { ...doc, filename, durationMs: Date.now() - start };
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error(`timed out waiting for ${filename}`);
}

async function listFiles(): Promise<string[]> {
  const out: string[] = [];
  for (const subdir of Object.keys(TYPE_BY_DIR)) {
    const full = join(SAMPLES_DIR, subdir);
    try {
      for (const f of await readdir(full)) {
        if (f.endsWith(".pdf")) out.push(join(full, f));
      }
    } catch {
      /* directory missing — skip */
    }
  }
  return out;
}

async function runPool<T, R>(items: T[], n: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results: R[] = [];
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      try {
        results[idx] = await fn(items[idx]!);
      } catch (err) {
        results[idx] = { error: String(err), filename: items[idx] } as unknown as R;
      }
    }
  }
  await Promise.all(Array.from({ length: n }, worker));
  return results;
}

async function main() {
  const base = process.env.API_BASE_URL;
  if (!base) throw new Error("API_BASE_URL env var is required");

  const files = await listFiles();
  if (files.length === 0) {
    console.log(`No sample files found in ${SAMPLES_DIR}. Run "pnpm samples" first.`);
    return;
  }
  const examples = Object.keys(TYPE_BY_DIR).flatMap((dir) =>
    files.filter((f) => basename(dirname(f)) === dir).slice(0, LABELED_PER_TYPE)
  );
  const rest = files.filter((f) => !examples.includes(f));
  console.log(`Uploading ${files.length} files to ${base} (concurrency ${CONCURRENCY})`);
  console.log(`  1/2 ${examples.length} labeled examples (type taken from the sample folder)`);

  const start = Date.now();
  const labeled = await runPool(examples, CONCURRENCY, (f) =>
    uploadAndWait(f, base, TYPE_BY_DIR[basename(dirname(f))])
  );
  console.log(`  2/2 ${rest.length} documents classified by k-NN against the examples`);
  const classified = await runPool(rest, CONCURRENCY, (f) => uploadAndWait(f, base));
  const results = [...labeled, ...classified];
  const totalMs = Date.now() - start;

  const byType: Record<string, number> = {};
  const byStatus: Record<string, number> = {};
  let durSum = 0;
  for (const r of results) {
    byType[r.docType] = (byType[r.docType] ?? 0) + 1;
    byStatus[r.status] = (byStatus[r.status] ?? 0) + 1;
    durSum += r.durationMs ?? 0;
    const flag = r.status === "done" ? "✓" : "✗";
    console.log(
      `  ${flag} ${r.filename}  type=${r.docType}  status=${r.status}  ${(r.durationMs / 1000).toFixed(1)}s${r.failedReason ? `  reason=${r.failedReason}` : ""}`
    );
  }

  console.log("\nSummary");
  console.log(`  files:       ${files.length}`);
  console.log(`  total time:  ${(totalMs / 1000).toFixed(1)}s`);
  console.log(`  avg per doc: ${(durSum / files.length / 1000).toFixed(1)}s`);
  console.log(`  by type:     ${JSON.stringify(byType)}`);
  console.log(`  by status:   ${JSON.stringify(byStatus)}`);
}

main().catch((err) => {
  console.error("seed failed:", err);
  process.exit(1);
});
