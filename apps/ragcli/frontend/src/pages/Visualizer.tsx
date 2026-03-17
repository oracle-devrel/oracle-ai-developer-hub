import { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import type Graph from 'graphology';
import { ArrowLeft, Network } from 'lucide-react';
import { useGraphData } from '../hooks/useGraphData';
import type { GraphFilters } from '../hooks/useGraphData';
import { buildGraph } from '../lib/graph-adapter';
import { GraphCanvas } from '../components/graph/GraphCanvas';
import type { GraphCanvasHandle } from '../components/graph/GraphCanvas';
import { FilterPanel } from '../components/graph/FilterPanel';
import { GraphSearch } from '../components/graph/GraphSearch';
import { DocumentSelector } from '../components/graph/DocumentSelector';

export function Visualizer() {
  const { data, loading, error, filters, setFilters, fetchGraph, fetchQueryGraph } = useGraphData();
  const [graph, setGraph] = useState<Graph | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const graphCanvasRef = useRef<GraphCanvasHandle>(null);

  useEffect(() => {
    fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (data && data.nodes.length > 0) {
      const g = buildGraph(data);
      setGraph(g);
    } else {
      setGraph(null);
    }
  }, [data]);

  const handleFilterApply = (newFilters: Partial<GraphFilters>) => {
    setFilters((prev: GraphFilters) => ({ ...prev, ...newFilters }));
    fetchGraph(newFilters);
  };

  const handleSearch = (query: string) => {
    fetchQueryGraph(query);
  };

  const handleFocusNode = useCallback((nodeId: string) => {
    graphCanvasRef.current?.focusNode(nodeId);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#06060a] overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-6 py-3 bg-surface border-b border-border-default z-20">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 text-[#8888a0] hover:text-[#e4e4ed] transition-colors"
          >
            <ArrowLeft size={16} />
            <span className="text-sm font-display">Back</span>
          </Link>
          <div className="h-4 w-px bg-border-default" />
          <div className="flex items-center gap-2">
            <Network size={16} className="text-accent" />
            <span className="text-[#e4e4ed] text-sm font-display font-medium">
              Vector Embedding Visualizer
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-[#5a5a70]">
          {data && (
            <>
              <span>{data.metadata.returned_chunks} nodes</span>
              <span>{data.edges.length} edges</span>
              <span>{data.metadata.embedding_model}</span>
              <span>{data.metadata.dimension}d</span>
            </>
          )}
        </div>
      </div>

      {/* Graph area */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-30">
            <div className="bg-surface border border-red-900/50 rounded-lg px-6 py-4 max-w-md">
              <p className="text-red-400 text-sm font-mono">{error}</p>
              <button
                onClick={() => fetchGraph()}
                className="mt-3 text-xs text-accent hover:text-[#e4e4ed] font-mono transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {loading && !graph && (
          <div className="absolute inset-0 flex items-center justify-center z-30">
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <span className="text-[#8888a0] text-sm font-mono">Loading embedding graph...</span>
            </div>
          </div>
        )}

        {graph && (
          <GraphCanvas
            ref={graphCanvasRef}
            graph={graph}
            highlightedDocumentId={selectedDocumentId}
          />
        )}

        {/* Document selector - left sidebar below filters */}
        <DocumentSelector
          data={data}
          selectedDocumentId={selectedDocumentId}
          onSelectDocument={setSelectedDocumentId}
          onFocusNode={handleFocusNode}
        />

        <FilterPanel filters={filters} onApply={handleFilterApply} loading={loading} />
        <GraphSearch onSearch={handleSearch} loading={loading} />

        {!loading && !error && data && data.nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center z-30">
            <Network size={48} className="text-[#2a2a3a] mb-4" />
            <p className="text-[#8888a0] text-sm font-display">No embeddings found</p>
            <p className="text-[#5a5a70] text-xs font-mono mt-1">Upload documents first, then come back here</p>
          </div>
        )}
      </div>
    </div>
  );
}
