import {
  BrainCircuit,
  Database,
  MessageSquareText,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { AppStatus } from "@oracle-mem0-ts-memory/shared";
import { createApiClient, type ApiClient } from "./api/client.js";
import { StatusStrip } from "./components/StatusStrip.js";
import { ChatWorkspace } from "./features/chat/ChatWorkspace.js";
import { MemoryExplorer } from "./features/memories/MemoryExplorer.js";
import { OracleInspector } from "./features/oracle/OracleInspector.js";

type View = "chat" | "memories" | "oracle";

const views = [
  ["chat", MessageSquareText, "Chat"],
  ["memories", BrainCircuit, "Memory explorer"],
  ["oracle", Database, "Oracle inspector"],
] as const;

function selectedUser() {
  return window.localStorage.getItem("mem0-demo-user") === "user-2"
    ? "user-2"
    : "user-1";
}

export function App({ client }: { client?: ApiClient }) {
  const api = useMemo(() => client ?? createApiClient(), [client]);
  const [view, setView] = useState<View>("chat");
  const [userId, setUserId] = useState(selectedUser);
  const [status, setStatus] = useState<AppStatus>();
  const [notice, setNotice] = useState("");
  const [seedFeedback, setSeedFeedback] = useState<{ message: string; error: boolean } | null>(null);
  const [busyAction, setBusyAction] = useState<"seed" | "reset" | null>(null);

  useEffect(() => {
    void api
      .getStatus()
      .then(setStatus)
      .catch(() => setNotice("Oracle status check failed. Is the API running?"));
  }, [api]);

  useEffect(() => {
    window.localStorage.setItem("mem0-demo-user", userId);
  }, [userId]);

  async function seed() {
    setBusyAction("seed");
    setNotice("");
    setSeedFeedback(null);
    try {
      const result = await api.seed();
      const message = result.added === 0
        ? "The ten demo memories are already loaded. Choose a starter question below."
        : `Loaded ${result.added} demo memories. Choose a starter question below.`;
      setNotice(message);
      setSeedFeedback({ message, error: false });
      setView("chat");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not load demo memories.";
      setNotice(message);
      setSeedFeedback({ message, error: true });
    } finally {
      setBusyAction(null);
    }
  }

  async function reset() {
    if (!window.confirm("Remove only this sample's MEM0 demo tables?")) return;

    setBusyAction("reset");
    setNotice("");
    try {
      const result = await api.reset();
      setNotice(`Removed ${result.dropped.length} demo tables.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not reset demo data.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__topline">
          <a className="brand" href="#workspace">
            <span className="brand__mark" aria-hidden="true">
              <Database size={21} />
            </span>
            <span>
              <strong>Oracle + Mem0</strong>
              <small>TypeScript memory sample</small>
            </span>
          </a>
          <StatusStrip status={status} />
        </div>

        <div className="hero__copy">
          <p className="kicker">Oracle AI Database + Mem0</p>
          <h1>Oracle Mem0 TypeScript Memory Assistant</h1>
          {status && <p className="mode-label">{status.setup.mode === "demo" ? "No-key demo mode" : "AI-powered mode"}</p>}
          <p className="hero__lead">
            Explore user-scoped memory, vector retrieval, and Oracle-backed
            evidence in a runnable TypeScript assistant.
          </p>
          <div className="hero__facts" aria-label="Sample capabilities">
            <span><ShieldCheck size={16} /> User-scoped</span>
            <span><Database size={16} /> Oracle vectors</span>
            <span><BrainCircuit size={16} /> Observable retrieval</span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="demo-guide" aria-labelledby="demo-title">
          <div className="demo-guide__intro">
            <p className="section-label">Guided walkthrough</p>
            <h2 id="demo-title">Try the demo</h2>
            <p>
              Load two sample profiles, choose whose memory is active, then ask a
              question that only their saved context can answer.
            </p>
            {status?.setup.mode === "demo" && <p>Answers quote saved memories. Chat does not automatically learn new facts in no-key mode; add them in Memory explorer.</p>}
          </div>

          <div className="demo-path">
            <article className="demo-step">
              <span className="demo-step__number">1</span>
              <div>
                <h3>Load sample context</h3>
                <p>Add ten example memories to the Oracle-backed store.</p>
                <button
                  className="primary-action"
                  disabled={busyAction !== null}
                  onClick={() => void seed()}
                >
                  <Sparkles size={16} />
                  {busyAction === "seed" ? "Loading…" : "Load demo memories"}
                </button>
                {seedFeedback && <p className={seedFeedback.error ? "demo-step__feedback demo-step__feedback--error" : "demo-step__feedback"} role={seedFeedback.error ? "alert" : "status"}>{seedFeedback.message}</p>}
              </div>
            </article>

            <article className="demo-step">
              <span className="demo-step__number">2</span>
              <div>
                <h3>Choose an identity</h3>
                <p>Memory retrieval stays isolated to the selected user.</p>
                <label className="demo-user-select">
                  <span>Demo user</span>
                  <select
                    aria-label="Demo user"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                  >
                    <option value="user-1">User 1</option>
                    <option value="user-2">User 2</option>
                  </select>
                </label>
              </div>
            </article>

            <article className="demo-step">
              <span className="demo-step__number">3</span>
              <div>
                <h3>Ask with memory</h3>
                <p>Use a starter question and inspect the evidence beside it.</p>
                <button className="secondary-action" onClick={() => setView("chat")}>
                  <MessageSquareText size={16} /> Open chat
                </button>
              </div>
            </article>
          </div>
        </section>

        <section className="workspace" id="workspace" aria-label="Memory workspace">
          <div className="workspace-bar">
            <nav className="workspace-nav" aria-label="Workspace">
              {views.map(([id, Icon, label]) => (
                <button
                  key={id}
                  className={view === id ? "active" : ""}
                  onClick={() => setView(id)}
                >
                  <Icon size={17} />
                  <span>{label}</span>
                </button>
              ))}
            </nav>

            <div className="workspace-meta">
              {notice && <p role="status">{notice}</p>}
              <code>{status?.setup.collectionName ?? "MEM0_TS_LOCAL_DEMO"}</code>
              <button
                className="reset-action"
                disabled={busyAction !== null}
                onClick={() => void reset()}
              >
                <RotateCcw size={14} /> Reset sample data
              </button>
            </div>
          </div>

          <div className="workspace-frame">
            {view === "chat" && <ChatWorkspace api={api} userId={userId} />}
            {view === "memories" && <MemoryExplorer api={api} userId={userId} />}
            {view === "oracle" && <OracleInspector api={api} />}
          </div>
        </section>
      </main>
    </div>
  );
}
