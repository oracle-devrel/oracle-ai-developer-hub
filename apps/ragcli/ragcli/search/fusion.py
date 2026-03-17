"""Reciprocal Rank Fusion for hybrid search."""

from collections import defaultdict
from typing import List, Dict, Any, Optional
from ..core.embedding import generate_embedding
from ..database.vector_ops import search_similar
from .bm25 import BM25Search
from ..knowledge.graph_search import GraphSearch
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HybridSearch:
    def __init__(self, conn, config: dict):
        self.conn = conn
        self.config = config
        search_config = config.get("search", {})
        self.k = search_config.get("rrf_k", 60)
        self.weights = search_config.get("weights", {"bm25": 1.0, "vector": 1.0, "graph": 0.8})
        self.strategy = search_config.get("strategy", "hybrid")
        self.bm25 = BM25Search(conn)
        self.graph_search = GraphSearch(conn, config)

    def search(
        self,
        query: str,
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        quality_scores: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        query_embedding = generate_embedding(
            query, self.config["ollama"]["embedding_model"], self.config
        )

        fetch_k = top_k * 3

        vector_results = search_similar(
            self.conn, query_embedding, fetch_k, 0.0, document_ids
        )

        bm25_results = []
        graph_chunk_ids = []

        if self.strategy in ("hybrid", "bm25_only"):
            bm25_results = self.bm25.search(query, fetch_k, document_ids)

        if self.strategy == "hybrid":
            graph_result = self.graph_search.subgraph_for_query(query_embedding, top_k=fetch_k)
            graph_chunk_ids = graph_result.get("chunk_ids", [])

        scores = defaultdict(float)
        chunk_data = {}

        for rank, chunk in enumerate(vector_results):
            cid = chunk["chunk_id"]
            scores[cid] += self.weights.get("vector", 1.0) / (self.k + rank + 1)
            chunk_data[cid] = chunk

        for rank, chunk in enumerate(bm25_results):
            cid = chunk["chunk_id"]
            scores[cid] += self.weights.get("bm25", 1.0) / (self.k + rank + 1)
            if cid not in chunk_data:
                chunk_data[cid] = chunk

        for rank, cid in enumerate(graph_chunk_ids):
            scores[cid] += self.weights.get("graph", 0.8) / (self.k + rank + 1)

        if quality_scores:
            boost_range = self.config.get("feedback", {}).get("quality_boost_range", 0.15)
            for cid in scores:
                q = quality_scores.get(cid, 0.5)
                scores[cid] *= (1.0 - boost_range + 2 * boost_range * q)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for cid, score in ranked:
            data = chunk_data.get(cid, {})
            results.append({
                "chunk_id": cid,
                "document_id": data.get("document_id", ""),
                "text": data.get("text", ""),
                "chunk_number": data.get("chunk_number", 0),
                "similarity_score": data.get("similarity_score", 0.0),
                "fusion_score": score,
            })

        return {
            "results": results,
            "query_embedding": query_embedding,
            "signal_counts": {
                "vector": len(vector_results),
                "bm25": len(bm25_results),
                "graph": len(graph_chunk_ids),
            },
        }
