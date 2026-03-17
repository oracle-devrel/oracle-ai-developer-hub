import { useState, useMemo } from 'react';
import { FileText, ChevronDown, ChevronRight, Hash, Eye, EyeOff } from 'lucide-react';
import type { GraphData } from '../../hooks/useGraphData';

interface DocumentInfo {
  documentId: string;
  documentName: string;
  chunkCount: number;
  nodeIds: string[];
}

interface DocumentSelectorProps {
  data: GraphData | null;
  selectedDocumentId: string | null;
  onSelectDocument: (docId: string | null) => void;
  onFocusNode: (nodeId: string) => void;
}

export function DocumentSelector({ data, selectedDocumentId, onSelectDocument, onFocusNode }: DocumentSelectorProps) {
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  const documents = useMemo(() => {
    if (!data) return [];
    const docMap = new Map<string, DocumentInfo>();
    for (const node of data.nodes) {
      if (node.node_type === 'query') continue;
      const existing = docMap.get(node.document_id);
      if (existing) {
        existing.chunkCount++;
        existing.nodeIds.push(node.id);
      } else {
        docMap.set(node.document_id, {
          documentId: node.document_id,
          documentName: node.document_name,
          chunkCount: 1,
          nodeIds: [node.id],
        });
      }
    }
    return Array.from(docMap.values()).sort((a, b) => b.chunkCount - a.chunkCount);
  }, [data]);

  const chunks = useMemo(() => {
    if (!data || !expandedDoc) return [];
    return data.nodes
      .filter(n => n.document_id === expandedDoc && n.node_type !== 'query')
      .sort((a, b) => a.chunk_number - b.chunk_number);
  }, [data, expandedDoc]);

  const handleDocClick = (docId: string) => {
    if (selectedDocumentId === docId) {
      onSelectDocument(null);
    } else {
      onSelectDocument(docId);
    }
  };

  const handleExpandToggle = (e: React.MouseEvent, docId: string) => {
    e.stopPropagation();
    setExpandedDoc(expandedDoc === docId ? null : docId);
  };

  if (!data || documents.length === 0) return null;

  return (
    <div className="absolute top-4 left-4 z-10 w-64 max-h-[calc(100vh-120px)] flex flex-col">
      <div className="bg-surface border border-border-default rounded-lg shadow-lg overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-border-subtle">
          <span className="flex items-center gap-2 text-sm font-medium font-display text-[#e4e4ed]">
            <FileText size={14} className="text-accent" />
            Documents
            <span className="text-[#5a5a70] text-xs ml-auto">{documents.length}</span>
          </span>
        </div>

        <div className="overflow-y-auto flex-1" style={{ maxHeight: 'calc(100vh - 240px)' }}>
          {documents.map((doc) => {
            const isSelected = selectedDocumentId === doc.documentId;
            const isExpanded = expandedDoc === doc.documentId;

            return (
              <div key={doc.documentId}>
                <div className={`w-full px-3 py-2.5 flex items-center gap-2 transition-all duration-150 group ${
                    isSelected
                      ? 'bg-accent/15 border-l-2 border-accent'
                      : 'hover:bg-[#1c1c28] border-l-2 border-transparent'
                  }`}
                >
                  <button
                    onClick={(e) => handleExpandToggle(e, doc.documentId)}
                    className="text-[#5a5a70] hover:text-[#8888a0] flex-shrink-0"
                    aria-label={isExpanded ? 'Collapse' : 'Expand'}
                  >
                    {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </button>

                  <button
                    onClick={() => handleDocClick(doc.documentId)}
                    className="flex-1 min-w-0 text-left"
                  >
                    <p className={`text-xs font-mono truncate ${
                      isSelected ? 'text-accent' : 'text-[#e4e4ed]'
                    }`}>
                      {doc.documentName}
                    </p>
                    <p className="text-[10px] text-[#5a5a70] mt-0.5">
                      {doc.chunkCount} chunk{doc.chunkCount !== 1 ? 's' : ''}
                    </p>
                  </button>

                  <span className={`flex-shrink-0 transition-opacity ${
                    isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                  }`}>
                    {isSelected
                      ? <Eye size={12} className="text-accent" />
                      : <EyeOff size={12} className="text-[#5a5a70]" />
                    }
                  </span>
                </div>

                {/* Expanded chunk list */}
                {isExpanded && (
                  <div className="bg-[#0a0a10]">
                    {chunks.map((chunk) => (
                      <button
                        key={chunk.id}
                        onClick={() => onFocusNode(chunk.id)}
                        className="w-full px-4 pl-8 py-1.5 flex items-center gap-2 text-left hover:bg-[#16161f] transition-colors"
                      >
                        <Hash size={10} className="text-[#5a5a70] flex-shrink-0" />
                        <span className="text-[10px] font-mono text-[#8888a0] flex-shrink-0">
                          {chunk.chunk_number}
                        </span>
                        <span className="text-[10px] text-[#5a5a70] truncate">
                          {chunk.text_preview.slice(0, 50)}...
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
