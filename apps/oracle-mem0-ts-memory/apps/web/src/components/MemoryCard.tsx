import { Database, Pencil, Trash2 } from "lucide-react";
import type { MemoryRecord } from "@oracle-mem0-ts-memory/shared";

export function MemoryCard({ memory, onEdit, onDelete }: { memory: MemoryRecord; onEdit?: () => void; onDelete?: () => void }) {
  return <article className="memory-card">
    <div className="memory-card__marker"><Database size={15} /></div>
    <div className="memory-card__body">
      <p>{memory.memory}</p>
      <div className="memory-meta"><span>{memory.id.slice(0, 12)}</span>{memory.score !== undefined && <span>{Math.round(memory.score * 100)}% match</span>}</div>
    </div>
    {(onEdit || onDelete) && <div className="icon-actions">
      {onEdit && <button className="icon-button" aria-label="Edit memory" onClick={onEdit}><Pencil size={15} /></button>}
      {onDelete && <button className="icon-button danger" aria-label="Delete memory" onClick={onDelete}><Trash2 size={15} /></button>}
    </div>}
  </article>;
}
