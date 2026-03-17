"""Similarity search orchestration for ragcli."""

import time
from typing import List, Dict, Any, Optional
from .embedding import generate_embedding
from ..database.oracle_client import OracleClient
from ..database.vector_ops import search_similar
from ..config.config_manager import load_config

def search_chunks(
    query: str,
    top_k: int,
    min_similarity: float,
    document_ids: Optional[List[str]] = None,
    config: dict = None
) -> Dict[str, Any]:
    """Perform similarity search for query, return results with metrics."""
    if config is None:
        config = load_config()
    
    start_time = time.perf_counter()
    
    # Generate query embedding
    emb_start = time.perf_counter()
    query_embedding = generate_embedding(query, config['ollama']['embedding_model'], config)
    emb_time = time.perf_counter() - emb_start
    
    # Get client and search
    client = OracleClient(config)
    search_start = time.perf_counter()
    conn = client.get_connection()
    try:
        results = search_similar(conn, query_embedding, top_k, min_similarity, document_ids)
    finally:
        conn.close()
    search_time = time.perf_counter() - search_start
    
    total_time = time.perf_counter() - start_time
    
    metrics = {
        'embedding_time_ms': emb_time * 1000,
        'search_time_ms': search_time * 1000,
        'total_time_ms': total_time * 1000,
        'num_results': len(results),
        'avg_similarity': sum(r['similarity_score'] for r in results) / len(results) if results else 0
    }
    
    return {
        'results': results,
        'query_embedding': query_embedding,
        'metrics': metrics
    }

# TODO: Log to QUERIES/QUERY_RESULTS, reranking, more advanced filtering
