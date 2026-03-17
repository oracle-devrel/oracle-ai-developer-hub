import { useState, useCallback } from 'react';
import axios from 'axios';

export interface GraphNode {
  id: string;
  document_id: string;
  document_name: string;
  chunk_number: number;
  text_preview: string;
  token_count: number;
  node_type: 'chunk' | 'query';
}

export interface GraphEdge {
  source: string;
  target: string;
  similarity: number;
}

export interface GraphMetadata {
  total_chunks: number;
  returned_chunks: number;
  embedding_model: string;
  dimension: number;
  min_similarity: number;
  top_k: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: GraphMetadata;
}

export interface GraphFilters {
  minSimilarity: number;
  topK: number;
  documentIds?: string[];
  limit: number;
}

const DEFAULT_FILTERS: GraphFilters = {
  minSimilarity: 0.5,
  topK: 10,
  limit: 500,
};

export function useGraphData() {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<GraphFilters>(DEFAULT_FILTERS);

  const fetchGraph = useCallback(async (overrideFilters?: Partial<GraphFilters>) => {
    const activeFilters = { ...filters, ...overrideFilters };
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {
        min_similarity: activeFilters.minSimilarity,
        top_k: activeFilters.topK,
        limit: activeFilters.limit,
      };
      if (activeFilters.documentIds?.length) {
        params.document_ids = activeFilters.documentIds.join(',');
      }
      const res = await axios.get<GraphData>('/api/embeddings/graph', { params });
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to fetch graph');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const fetchQueryGraph = useCallback(async (query: string, overrideFilters?: Partial<GraphFilters>) => {
    const activeFilters = { ...filters, ...overrideFilters };
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post<GraphData>('/api/embeddings/graph/query', {
        query,
        min_similarity: activeFilters.minSimilarity,
        top_k: activeFilters.topK,
        document_ids: activeFilters.documentIds || null,
        limit: activeFilters.limit,
      });
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to fetch query graph');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    fetchGraph,
    fetchQueryGraph,
  };
}
