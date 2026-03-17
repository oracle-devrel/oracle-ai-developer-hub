"""Similarity heatmap visualization utilities."""

import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity_matrix(embeddings: List[List[float]], query_embedding: Optional[List[float]] = None) -> np.ndarray:
    """Compute cosine similarity matrix between embeddings.

    Args:
        embeddings: List of embedding vectors
        query_embedding: Optional query embedding to include in matrix

    Returns:
        Similarity matrix as numpy array
    """
    if not embeddings:
        return np.array([]).reshape(0, 0)

    embeddings_array = np.array(embeddings)

    if query_embedding:
        query_array = np.array([query_embedding])
        all_embeddings = np.vstack([query_array, embeddings_array])
    else:
        all_embeddings = embeddings_array

    # Compute cosine similarity
    similarity_matrix = cosine_similarity(all_embeddings)

    return similarity_matrix


def create_similarity_heatmap(
    embeddings: List[List[float]],
    labels: Optional[List[str]] = None,
    query_embedding: Optional[List[float]] = None,
    query_label: str = "Query",
    title: str = "Similarity Heatmap",
    threshold: Optional[float] = None
) -> go.Figure:
    """Create interactive similarity heatmap.

    Args:
        embeddings: List of document chunk embeddings
        labels: Optional labels for each embedding
        query_embedding: Optional query embedding to include
        query_label: Label for query if provided
        title: Plot title
        threshold: Optional similarity threshold for filtering

    Returns:
        Plotly figure object
    """
    if not embeddings:
        # Return empty figure
        fig = go.Figure()
        fig.update_layout(title="No embeddings available")
        return fig

    similarity_matrix = compute_similarity_matrix(embeddings, query_embedding)

    # Prepare labels
    if query_embedding:
        all_labels = [query_label] + (labels if labels else [f"Doc {i+1}" for i in range(len(embeddings))])
    else:
        all_labels = labels if labels else [f"Doc {i+1}" for i in range(len(embeddings))]

    # Apply threshold if specified
    if threshold is not None:
        display_matrix = np.where(similarity_matrix >= threshold, similarity_matrix, np.nan)
    else:
        display_matrix = similarity_matrix

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=display_matrix,
        x=all_labels,
        y=all_labels,
        colorscale='RdYlBu_r',  # Red for low similarity, blue for high
        colorbar=dict(title="Cosine Similarity"),
        hovertemplate='%{x} ↔ %{y}<br>Similarity: %{z:.3f}<extra></extra>',
        zmin=0 if threshold is None else threshold,
        zmax=1
    ))

    # Add threshold annotation if applied
    annotations = []
    if threshold is not None:
        annotations.append(
            dict(
                text=f"Threshold: {threshold}",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
        )

    fig.update_layout(
        title=title,
        xaxis=dict(
            title="Documents",
            tickangle=-45,
            side="bottom"
        ),
        yaxis=dict(
            title="Documents",
            autorange="reversed"  # So that diagonal is from top-left to bottom-right
        ),
        annotations=annotations
    )

    return fig


def create_similarity_bar_chart(
    similarities: List[float],
    labels: List[str],
    title: str = "Similarity Scores",
    top_k: Optional[int] = None
) -> go.Figure:
    """Create bar chart of similarity scores.

    Args:
        similarities: List of similarity scores
        labels: Corresponding labels
        title: Chart title
        top_k: Show only top-k results

    Returns:
        Plotly figure object
    """
    if top_k and top_k < len(similarities):
        # Sort by similarity descending and take top-k
        sorted_indices = np.argsort(similarities)[::-1][:top_k]
        similarities = [similarities[i] for i in sorted_indices]
        labels = [labels[i] for i in sorted_indices]

    # Color bars based on similarity value
    colors = ['red' if s < 0.5 else 'orange' if s < 0.7 else 'green' for s in similarities]

    fig = go.Figure(data=go.Bar(
        x=labels,
        y=similarities,
        marker_color=colors,
        text=[f'{s:.3f}' for s in similarities],
        textposition='auto',
        hovertemplate='%{x}<br>Similarity: %{y:.3f}<extra></extra>'
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title="Documents",
            tickangle=-45
        ),
        yaxis=dict(
            title="Cosine Similarity",
            range=[0, 1]
        ),
        showlegend=False
    )

    return fig


def get_similarity_data_for_visualization(query_id: Optional[str] = None, config: Optional[dict] = None) -> Tuple[List[List[float]], List[str], Optional[List[float]]]:
    """Get similarity data for visualization from recent query.

    Args:
        query_id: Optional query ID to get similarity data
        config: Configuration dictionary

    Returns:
        Tuple of (embeddings, labels, similarities)
    """
    # TODO: Implement database queries to get embeddings and similarities
    # For now, return empty - this would need database access
    if config is None:
        from ..config.config_manager import load_config
        config = load_config()

    # Placeholder - would need to query query_results and chunks tables
    embeddings = []
    labels = []
    similarities = None

    return embeddings, labels, similarities


def format_similarity_score(score: float) -> str:
    """Format similarity score for display."""
    if score >= 0.8:
        return f"■ {score:.3f}"  # High similarity
    elif score >= 0.5:
        return f"▬ {score:.3f}"  # Medium similarity
    else:
        return f"□ {score:.3f}"  # Low similarity
