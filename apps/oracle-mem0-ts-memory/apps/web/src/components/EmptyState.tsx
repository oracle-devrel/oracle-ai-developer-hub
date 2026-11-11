import type { ReactNode } from "react";

export function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return <div className="empty-state"><span>{icon}</span><h3>{title}</h3><p>{detail}</p></div>;
}
