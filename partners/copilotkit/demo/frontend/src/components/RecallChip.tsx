"use client";

interface RecallChipProps {
  memories?: string;
}

export function RecallChip({ memories }: RecallChipProps) {
  const hasMemories = Boolean(memories && memories.trim().length > 0);

  return (
    <span
      className="text-xs rounded-full bg-gray-100 px-2.5 py-1 text-gray-600 inline-flex items-center gap-1"
      title={hasMemories ? memories : undefined}
    >
      🧠{" "}
      {hasMemories
        ? "Remembered your preferences"
        : "Recalling your preferences…"}
    </span>
  );
}
