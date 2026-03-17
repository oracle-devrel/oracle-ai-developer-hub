"""Retrieval chain visualization for ragcli."""

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich import print as rprint
from typing import Dict, Any
import time

console = Console()

def show_retrieval_chain(result: Dict[str, Any], console_output: bool = True):
    """Show retrieval chain in terminal."""
    if console_output:
        tree = Tree("RAG Retrieval Chain", style="bold cyan")
        
        # Query
        query_node = tree.add("1. Query Input")
        query_node.add(f"[Query]: {result.get('query', 'N/A')}")
        query_node.add(f"[Tokens]: {result['metrics'].get('prompt_tokens', 'N/A')}")
        
        # Embedding
        emb_node = tree.add("2. Embedding Generation")
        emb_node.add(f"[Time]: {result['metrics']['embedding_time_ms']:.2f}ms")
        emb_node.add("[Vector]: 768-dim (nomic-embed-text)")
        
        # Search
        search_node = tree.add("3. Vector Similarity Search")
        search_node.add(f"[Top-K]: {len(result['results'])} results")
        search_node.add(f"[Avg Similarity]: {result['metrics'].get('avg_similarity', 0):.3f}")
        search_node.add(f"[Time]: {result['metrics']['search_time_ms']:.2f}ms")
        
        for r in result['results'][:3]:  # Top 3
            chunk_node = search_node.add(f"Chunk from {r['document_id']}")
            chunk_node.add(f"Score: {r['similarity_score']:.3f}")
            chunk_node.add(f"Excerpt: {r['text'][:100]}...")
        
        # Context Assembly
        context_node = tree.add("4. Context Assembly")
        context_node.add(f"[Total Context Tokens]: {result['metrics']['prompt_tokens'] - len(result.get('query', '').split())}")
        
        # LLM Generation
        llm_node = tree.add("5. LLM Generation")
        llm_node.add(f"[Model]: llama2")
        llm_node.add(f"[Time]: {result['metrics']['generation_time_ms']:.2f}ms")
        llm_node.add(f"[Response Tokens]: {result['metrics']['completion_tokens']}")
        llm_node.add(f"[Response]: {result['response'][:200]}...")
        
        # Total
        total_node = tree.add("Total Time")
        total_node.add(f"{result['metrics']['total_time_ms']:.2f}ms")
        
        console.print(tree)
    else:
        # For web, return plotly fig (stub)
        from plotly.graph_objects import Figure
        fig = Figure()
        fig.add_annotation(text="Retrieval Chain (Terminal only for now)")
        return fig

# TODO: Expandable sections, real-time updates, token-level viz
