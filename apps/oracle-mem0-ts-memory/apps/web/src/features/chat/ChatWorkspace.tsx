import { ArrowUp, BrainCircuit, LoaderCircle, RotateCcw, Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { ChatResponse } from "@oracle-mem0-ts-memory/shared";
import type { ApiClient } from "../../api/client.js";
import { EmptyState } from "../../components/EmptyState.js";
import { MemoryCard } from "../../components/MemoryCard.js";

type Turn = { question: string; response: ChatResponse };

const prompts: Record<string, string[]> = {
  "user-1": ["What drink do I prefer, and where should I sit when travelling?", "What do you remember about my travel preferences?"],
  "user-2": ["What should I order for lunch, and how should you format my meeting notes?", "What do you remember about how I work?"],
};

function userLabel(userId: string): string { return userId === "user-2" ? "User 2" : "User 1"; }

export function ChatWorkspace({ api, userId }: { api: ApiClient; userId: string }) {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!message.trim() || busy) return;
    const question = message.trim(); setMessage(""); setBusy(true); setError("");
    try {
      const response = await api.chat({ userId, message: question });
      setTurns((items) => [...items, { question, response }]);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The request failed."); }
    finally { setBusy(false); }
  }
  const evidence = turns.at(-1)?.response.retrievedMemories ?? [];
  return <div className="workspace-grid">
    <section className="chat-pane">
      <header className="pane-heading"><div><span className="section-label">Conversation</span><h2>Memory-aware chat</h2><p>Ask naturally. The assistant retrieves only this user's saved context.</p></div>{turns.length > 0 && <button className="quiet-button" onClick={() => setTurns([])}><RotateCcw size={14} /> Clear</button>}</header>
      <div className="transcript" aria-live="polite">
        {turns.length === 0 && <EmptyState icon={<BrainCircuit size={28} />} title={`Ready for ${userLabel(userId)}`} detail="Load the demo memories, choose a starter below, and watch Oracle return the evidence used for the answer." />}
        {turns.map((turn, index) => <div className="turn" key={`${turn.question}-${index}`}>
          <div className="message message--user"><span>You</span><p>{turn.question}</p></div>
          <div className="message message--assistant"><span>Assistant</span><p>{turn.response.answer}</p></div>
        </div>)}
        {busy && <div className="thinking"><LoaderCircle className="spin" size={16} /> Retrieving memory and composing…</div>}
        {error && <p role="alert" className="error-banner">{error}</p>}
      </div>
      <div className="starter-prompts" aria-label={`Starter prompts for ${userLabel(userId)}`}><span>Try a question</span><div>{(prompts[userId] ?? prompts["user-1"]!).map((prompt) => <button type="button" key={prompt} onClick={() => setMessage(prompt)}>{prompt}</button>)}</div></div>
      <form className="composer" onSubmit={submit}>
        <label htmlFor="chat-message">Message</label>
        <textarea id="chat-message" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Ask something that benefits from memory…" rows={3} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} />
        <button type="submit" disabled={busy || !message.trim()}>Send <ArrowUp size={16} /></button>
      </form>
    </section>
    <aside className="evidence-pane">
      <header className="pane-heading"><div><span className="section-label">Retrieval trace</span><h2>Oracle evidence</h2><p>See exactly which vector memories informed the latest answer.</p></div><span className="count-chip">{evidence.length}</span></header>
      <p className="scope-note"><span>Scoped identity</span><strong>{userLabel(userId)}</strong></p>
      <div className="memory-list">{evidence.length ? evidence.map((item) => <MemoryCard key={item.id} memory={item} />) : <EmptyState icon={<Search size={24} />} title="No retrieval yet" detail="Relevant Oracle vectors will appear here after a message." />}</div>
    </aside>
  </div>;
}
