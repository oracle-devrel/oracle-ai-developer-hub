interface NodeInfoBarProps {
  nodeData: Record<string, any>;
  onFocus: () => void;
}

export function NodeInfoBar({ nodeData, onFocus }: NodeInfoBarProps) {
  const isQuery = nodeData.nodeType === 'query';

  return (
    <div className="absolute bottom-0 left-0 right-0 bg-surface border-t border-border-default px-6 py-3 z-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: nodeData.color }}
          />
          <div>
            <span className="text-[#e4e4ed] text-sm font-mono">
              {isQuery ? 'Query Node' : `${nodeData.documentName} — Chunk #${nodeData.chunkNumber}`}
            </span>
            <span className="text-[#5a5a70] text-xs ml-4">
              {nodeData.tokenCount > 0 && `${nodeData.tokenCount} tokens`}
              {nodeData.maxSimilarity > 0 && ` | Max similarity: ${nodeData.maxSimilarity.toFixed(4)}`}
            </span>
          </div>
        </div>
        <button
          onClick={onFocus}
          className="text-xs text-accent hover:text-[#e4e4ed] transition-colors font-mono"
        >
          Focus
        </button>
      </div>
      {nodeData.textPreview && (
        <p className="text-[#8888a0] text-xs mt-1 font-mono truncate max-w-3xl">
          {nodeData.textPreview}
        </p>
      )}
    </div>
  );
}
