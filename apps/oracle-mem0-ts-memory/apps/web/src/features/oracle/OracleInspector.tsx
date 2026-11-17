import { Database, RefreshCw, TableProperties } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { OracleInspection } from "@oracle-mem0-ts-memory/shared";
import type { ApiClient } from "../../api/client.js";

export function OracleInspector({ api }: { api: ApiClient }) {
  const [data, setData] = useState<OracleInspection>(); const [error, setError] = useState("");
  const load = useCallback(async () => { try { setData(await api.inspect()); setError(""); } catch (e) { setError(e instanceof Error ? e.message : "Inspection failed"); } }, [api]);
  useEffect(() => { void load(); }, [load]);
  return <section className="single-pane inspector">
    <header className="pane-heading"><div><span className="section-label">Physical storage</span><h2>Oracle inspector</h2><p>Inspect the collection, vector column, row count, and database indexes.</p></div><button className="quiet-button" onClick={() => void load()}><RefreshCw size={14} /> Refresh</button></header>
    {error && <p role="alert" className="error-banner">{error}</p>}
    <div className="inspector-hero"><Database size={30} /><div><span>Collection</span><strong>{data?.collectionName ?? "Loading…"}</strong></div><b>{data?.rowCount ?? 0} rows</b></div>
    <div className="inspection-grid"><div><h3><TableProperties size={17} /> Columns</h3>{data?.columns.length ? <table><tbody>{data.columns.map((col) => <tr key={col.name}><th>{col.name}</th><td>{col.dataType}</td></tr>)}</tbody></table> : <p>No schema metadata yet.</p>}</div><div><h3>Vector indexes</h3>{data?.vectorIndexes.length ? data.vectorIndexes.map((index) => <p key={index.name}>{index.name} · {index.status}</p>) : <p>No vector index reported.</p>}</div></div>
  </section>;
}
