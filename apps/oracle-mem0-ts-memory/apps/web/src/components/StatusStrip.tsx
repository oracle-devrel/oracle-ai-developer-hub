import { CircleCheck, CircleX, Database } from "lucide-react";
import type { AppStatus } from "@oracle-mem0-ts-memory/shared";

export function StatusStrip({ status }: { status?: AppStatus }) {
  const connected = Boolean(status?.database.connected);
  const stateLabel = status === undefined ? "checking" : connected ? "connected" : "unavailable";
  return <div className={connected ? "oracle-status oracle-status--ok" : "oracle-status"} aria-label="Oracle status">
    <span className="oracle-status__icon"><Database size={18} /></span>
    <div className="oracle-status__copy"><strong>Oracle Database {stateLabel}</strong><small>{status?.database.detail ?? "Checking local connection…"}</small></div>
    {connected ? <CircleCheck className="oracle-status__check" size={17} /> : <CircleX size={17} />}
  </div>;
}
