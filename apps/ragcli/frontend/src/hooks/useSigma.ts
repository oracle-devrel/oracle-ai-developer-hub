import { useEffect, useRef, useState, useCallback } from 'react';
import Sigma from 'sigma';
import Graph from 'graphology';
import EdgeCurveProgram from '@sigma/edge-curve';
import FA2Layout from 'graphology-layout-forceatlas2/worker';
import { dimColor } from '../lib/graph-adapter';

export interface SigmaState {
  selectedNode: string | null;
  hoveredNode: string | null;
  layoutRunning: boolean;
}

interface UseSigmaOptions {
  highlightedDocumentId?: string | null;
}

export function useSigma(
  containerRef: React.RefObject<HTMLDivElement | null>,
  graph: Graph | null,
  options: UseSigmaOptions = {},
) {
  const sigmaRef = useRef<Sigma | null>(null);
  const layoutRef = useRef<FA2Layout | null>(null);
  const selectedNodeRef = useRef<string | null>(null);
  const hoveredNodeRef = useRef<string | null>(null);
  const highlightedDocRef = useRef<string | null>(null);
  const isDraggingRef = useRef(false);
  const draggedNodeRef = useRef<string | null>(null);
  const [state, setState] = useState<SigmaState>({
    selectedNode: null,
    hoveredNode: null,
    layoutRunning: false,
  });

  // Keep highlighted doc ref in sync
  useEffect(() => {
    highlightedDocRef.current = options.highlightedDocumentId ?? null;
    sigmaRef.current?.refresh();
  }, [options.highlightedDocumentId]);

  useEffect(() => {
    if (!containerRef.current || !graph) return;

    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }
    if (layoutRef.current) {
      layoutRef.current.kill();
      layoutRef.current = null;
    }

    const nodeCount = graph.order;
    let gravity = 0.8, scalingRatio = 15, slowDown = 1;
    if (nodeCount > 500) { gravity = 0.5; scalingRatio = 30; slowDown = 2; }
    if (nodeCount > 2000) { gravity = 0.3; scalingRatio = 60; slowDown = 3; }

    const sigma = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,
      renderEdgeLabels: false,
      labelRenderedSizeThreshold: 8,
      labelDensity: 0.15,
      labelGridCellSize: 70,
      labelFont: '"JetBrains Mono", monospace',
      labelColor: { color: '#e4e4ed' },
      labelSize: 11,
      stagePadding: 50,
      // Performance: hide edges/labels during camera movement
      hideEdgesOnMove: true,
      hideLabelsOnMove: true,
      // Smooth zoom
      zoomToSizeRatioFunction: (x) => x,
      edgeProgramClasses: {
        curved: EdgeCurveProgram,
      },
      nodeReducer: (node, data) => {
        const res = { ...data };
        const selected = selectedNodeRef.current;
        const hovered = hoveredNodeRef.current;
        const highlightedDoc = highlightedDocRef.current;

        // Document highlighting takes precedence when active
        if (highlightedDoc) {
          const nodeDocId = graph.getNodeAttribute(node, 'documentId');
          if (nodeDocId === highlightedDoc) {
            res.highlighted = true;
            res.size = (data.size || 6) * 1.5;
            res.color = '#7c3aed'; // accent purple
          } else {
            res.color = dimColor(data.color || '#475569', 0.15);
            res.size = (data.size || 6) * 0.5;
            res.label = '';
          }
          // If a node is also selected, boost it further
          if (node === selected) {
            res.size = (data.size || 6) * 2;
            res.highlighted = true;
          }
          return res;
        }

        if (selected) {
          if (node === selected) {
            res.highlighted = true;
            res.size = (data.size || 6) * 1.8;
          } else if (graph.hasEdge(node, selected) || graph.hasEdge(selected, node)) {
            res.size = (data.size || 6) * 1.3;
          } else {
            res.color = dimColor(data.color || '#475569', 0.2);
            res.size = (data.size || 6) * 0.5;
            res.label = '';
          }
        } else if (hovered) {
          if (node === hovered) {
            res.highlighted = true;
            res.size = (data.size || 6) * 1.4;
          } else if (graph.hasEdge(node, hovered) || graph.hasEdge(hovered, node)) {
            res.size = (data.size || 6) * 1.2;
          } else {
            res.color = dimColor(data.color || '#475569', 0.3);
            res.size = (data.size || 6) * 0.7;
            res.label = '';
          }
        }

        return res;
      },
      edgeReducer: (edge, data) => {
        const res = { ...data };
        const selected = selectedNodeRef.current;
        const highlightedDoc = highlightedDocRef.current;

        if (highlightedDoc) {
          const extremities = graph.extremities(edge);
          const srcDoc = graph.getNodeAttribute(extremities[0], 'documentId');
          const tgtDoc = graph.getNodeAttribute(extremities[1], 'documentId');
          if (srcDoc !== highlightedDoc && tgtDoc !== highlightedDoc) {
            res.hidden = true;
          } else {
            res.color = '#7c3aed';
            res.size = (data.size || 1) * 1.5;
          }
          return res;
        }

        if (selected) {
          const extremities = graph.extremities(edge);
          if (extremities[0] !== selected && extremities[1] !== selected) {
            res.hidden = true;
          }
        }

        return res;
      },
    });

    // --- Node click ---
    sigma.on('clickNode', ({ node }) => {
      // Ignore clicks that were actually drags
      if (isDraggingRef.current) return;
      const newSelected = selectedNodeRef.current === node ? null : node;
      selectedNodeRef.current = newSelected;
      setState(prev => ({ ...prev, selectedNode: newSelected }));
      sigma.refresh();
    });

    sigma.on('clickStage', () => {
      if (isDraggingRef.current) return;
      selectedNodeRef.current = null;
      setState(prev => ({ ...prev, selectedNode: null }));
      sigma.refresh();
    });

    // --- Node hover ---
    sigma.on('enterNode', ({ node }) => {
      hoveredNodeRef.current = node;
      setState(prev => ({ ...prev, hoveredNode: node }));
      if (containerRef.current) containerRef.current.style.cursor = 'grab';
      sigma.refresh();
    });

    sigma.on('leaveNode', () => {
      if (!isDraggingRef.current) {
        hoveredNodeRef.current = null;
        setState(prev => ({ ...prev, hoveredNode: null }));
        if (containerRef.current) containerRef.current.style.cursor = 'default';
        sigma.refresh();
      }
    });

    // --- Node dragging ---
    sigma.on('downNode', (e) => {
      isDraggingRef.current = true;
      draggedNodeRef.current = e.node;
      // Fix the node so ForceAtlas2 doesn't move it
      graph.setNodeAttribute(e.node, 'fixed', true);
      // Disable sigma camera dragging while we drag a node
      sigma.getCamera().disable();
      if (containerRef.current) containerRef.current.style.cursor = 'grabbing';
    });

    const handleMouseMove = (e: any) => {
      if (!isDraggingRef.current || !draggedNodeRef.current) return;
      // Convert viewport coords to graph coords
      const pos = sigma.viewportToGraph(e);
      graph.setNodeAttribute(draggedNodeRef.current, 'x', pos.x);
      graph.setNodeAttribute(draggedNodeRef.current, 'y', pos.y);
      // Prevent sigma from treating this as a camera pan
      e.preventSigmaDefault();
      e.original.preventDefault();
      e.original.stopPropagation();
    };

    const handleMouseUp = () => {
      if (draggedNodeRef.current) {
        graph.removeNodeAttribute(draggedNodeRef.current, 'fixed');
      }
      isDraggingRef.current = false;
      draggedNodeRef.current = null;
      sigma.getCamera().enable();
      if (containerRef.current) containerRef.current.style.cursor = 'default';
    };

    const handleMouseDown = () => {
      // Only for stage clicks — update cursor
      if (!isDraggingRef.current && containerRef.current) {
        containerRef.current.style.cursor = 'default';
      }
    };

    const captor = sigma.getMouseCaptor();
    captor.on('mousemovebody', handleMouseMove);
    captor.on('mouseup', handleMouseUp);
    captor.on('mousedown', handleMouseDown);

    sigmaRef.current = sigma;

    // --- ForceAtlas2 layout (continuous, user-controlled) ---
    const layout = new FA2Layout(graph, {
      settings: {
        gravity,
        scalingRatio,
        slowDown,
        barnesHutOptimize: nodeCount > 100,
        barnesHutTheta: 0.6,
        strongGravityMode: false,
        adjustSizes: true,
      },
    });

    layout.start();
    layoutRef.current = layout;
    setState(prev => ({ ...prev, layoutRunning: true }));

    // Auto-stop layout after convergence (longer for larger graphs)
    const autoStopMs = nodeCount > 2000 ? 30000 : nodeCount > 500 ? 15000 : 8000;
    const autoStopTimer = setTimeout(() => {
      if (layoutRef.current) {
        layoutRef.current.stop();
        setState(prev => ({ ...prev, layoutRunning: false }));
      }
    }, autoStopMs);

    return () => {
      clearTimeout(autoStopTimer);
      // Clean up mouse captor listeners before killing sigma
      const cap = sigmaRef.current?.getMouseCaptor();
      if (cap) {
        cap.off('mousemovebody', handleMouseMove);
        cap.off('mouseup', handleMouseUp);
        cap.off('mousedown', handleMouseDown);
      }
      if (layoutRef.current) {
        layoutRef.current.kill();
        layoutRef.current = null;
      }
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
      }
    };
  }, [graph, containerRef]);

  const zoomIn = useCallback(() => {
    sigmaRef.current?.getCamera().animatedZoom({ duration: 200 });
  }, []);

  const zoomOut = useCallback(() => {
    sigmaRef.current?.getCamera().animatedUnzoom({ duration: 200 });
  }, []);

  const resetCamera = useCallback(() => {
    sigmaRef.current?.getCamera().animatedReset({ duration: 300 });
  }, []);

  const focusNode = useCallback((nodeId: string) => {
    if (!sigmaRef.current || !graph?.hasNode(nodeId)) return;
    const displayData = sigmaRef.current.getNodeDisplayData(nodeId);
    if (!displayData) return;
    sigmaRef.current.getCamera().animate(
      { x: displayData.x, y: displayData.y, ratio: 0.15 },
      { duration: 500 },
    );
  }, [graph]);

  const toggleLayout = useCallback(() => {
    if (!layoutRef.current) return;
    if (state.layoutRunning) {
      layoutRef.current.stop();
      setState(prev => ({ ...prev, layoutRunning: false }));
    } else {
      layoutRef.current.start();
      setState(prev => ({ ...prev, layoutRunning: true }));
    }
  }, [state.layoutRunning]);

  return {
    sigma: sigmaRef,
    state,
    zoomIn,
    zoomOut,
    resetCamera,
    focusNode,
    toggleLayout,
  };
}
