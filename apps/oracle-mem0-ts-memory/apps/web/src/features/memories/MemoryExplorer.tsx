import { Brain, Plus, Search } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { MemoryRecord } from "@oracle-mem0-ts-memory/shared";
import type { ApiClient } from "../../api/client.js";
import { EmptyState } from "../../components/EmptyState.js";
import { MemoryCard } from "../../components/MemoryCard.js";

export function MemoryExplorer({ api, userId }: { api: ApiClient; userId: string }) {
  const [items, setItems] = useState<MemoryRecord[]>([]); const [query, setQuery] = useState(""); const [text, setText] = useState(""); const [error, setError] = useState("");
  const load = useCallback(async (search?: string) => { try { setItems(await api.listMemories(userId, search)); setError(""); } catch (e) { setError(e instanceof Error ? e.message : "Could not load memories"); } }, [api, userId]);
  useEffect(() => { void load(); }, [load]);
  async function create(event: FormEvent) { event.preventDefault(); if (!text.trim()) return; await api.createMemory(userId, text.trim(), { source: "manual" }); setText(""); await load(query); }
  async function edit(memory: MemoryRecord) { const replacement = window.prompt("Update this memory", memory.memory); if (replacement?.trim()) { await api.updateMemory(userId, memory.id, replacement.trim()); await load(query); } }
  async function remove(memory: MemoryRecord) { if (!window.confirm("Delete this memory?")) return; await api.deleteMemory(userId, memory.id); setItems((current) => current.filter((item) => item.id !== memory.id)); }
  return <section className="single-pane">
    <header className="pane-heading"><div><span className="section-label">Persistent context</span><h2>Memory explorer</h2><p>Search and manage the memories stored for this demo user.</p></div><span className="count-chip">{items.length}</span></header>
    <div className="memory-tools">
      <form className="search-box" onSubmit={(e) => { e.preventDefault(); void load(query); }}><Search size={17} /><label className="sr-only" htmlFor="memory-search">Search memories</label><input id="memory-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Semantic search" /><button>Search</button></form>
      <form className="add-memory" onSubmit={create}><label htmlFor="memory-text">Add a memory</label><div><input id="memory-text" value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. Prefers window seats" /><button><Plus size={16} /> Add</button></div></form>
    </div>
    {error && <p role="alert" className="error-banner">{error}</p>}
    <div className="memory-list memory-list--wide">{items.length ? items.map((item) => <MemoryCard key={item.id} memory={item} onEdit={() => void edit(item)} onDelete={() => void remove(item)} />) : <EmptyState icon={<Brain size={26} />} title="No memories for this user" detail="Add one manually or start a conversation." />}</div>
  </section>;
}
