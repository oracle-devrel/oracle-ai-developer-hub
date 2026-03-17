import { useRef, useImperativeHandle, forwardRef } from 'react';
import type Graph from 'graphology';
import { useSigma } from '../../hooks/useSigma';
import { GraphControls } from './GraphControls';
import { NodeInfoBar } from './NodeInfoBar';

export interface GraphCanvasHandle {
  focusNode: (nodeId: string) => void;
}

interface GraphCanvasProps {
  graph: Graph | null;
  highlightedDocumentId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
}

export const GraphCanvas = forwardRef<GraphCanvasHandle, GraphCanvasProps>(function GraphCanvas(
  { graph, highlightedDocumentId, onNodeSelect },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { state, zoomIn, zoomOut, resetCamera, focusNode, toggleLayout } = useSigma(
    containerRef,
    graph,
    { highlightedDocumentId },
  );

  useImperativeHandle(ref, () => ({ focusNode }), [focusNode]);

  const selectedNodeData = state.selectedNode && graph?.hasNode(state.selectedNode)
    ? graph.getNodeAttributes(state.selectedNode)
    : null;

  const hoveredNodeData = state.hoveredNode && graph?.hasNode(state.hoveredNode)
    ? graph.getNodeAttributes(state.hoveredNode)
    : null;

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full"
        style={{ cursor: 'default', background: '#06060a' }}
      />

      {hoveredNodeData && !state.selectedNode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-surface border border-border-default rounded-lg px-4 py-2 shadow-lg z-10 max-w-md pointer-events-none">
          <p className="text-[#e4e4ed] text-sm font-mono truncate">
            {hoveredNodeData.nodeType === 'query' ? 'Query' : hoveredNodeData.documentName}
            {hoveredNodeData.nodeType !== 'query' && ` #${hoveredNodeData.chunkNumber}`}
          </p>
          <p className="text-[#8888a0] text-xs mt-1 line-clamp-2">{hoveredNodeData.textPreview}</p>
        </div>
      )}

      {selectedNodeData && (
        <NodeInfoBar
          nodeData={selectedNodeData}
          onFocus={() => state.selectedNode && focusNode(state.selectedNode)}
        />
      )}

      <GraphControls
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onReset={resetCamera}
        onToggleLayout={toggleLayout}
        layoutRunning={state.layoutRunning}
      />
    </div>
  );
});
