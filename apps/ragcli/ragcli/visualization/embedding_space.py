"""Embedding space visualization utilities."""

import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional, Tuple
from sklearn.manifold import TSNE
import umap
from ..core.embedding import generate_embedding
from ..config.config_manager import load_config


def project_embeddings_2d(embeddings: List[List[float]], method: str = 'umap') -> np.ndarray:
    """Project high-dimensional embeddings to 2D.

    Args:
        embeddings: List of embedding vectors
        method: 'umap' or 'tsne'

    Returns:
        2D coordinates as numpy array (n_samples, 2)
    """
    if not embeddings:
        return np.array([]).reshape(0, 2)

    embeddings_array = np.array(embeddings)

    if method.lower() == 'umap':
        reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
    elif method.lower() == 'tsne':
        reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
    else:
        raise ValueError(f"Unknown method: {method}. Use 'umap' or 'tsne'")

    return reducer.fit_transform(embeddings_array)


def project_embeddings_3d(embeddings: List[List[float]], method: str = 'umap') -> np.ndarray:
    """Project high-dimensional embeddings to 3D.

    Args:
        embeddings: List of embedding vectors
        method: 'umap' or 'tsne'

    Returns:
        3D coordinates as numpy array (n_samples, 3)
    """
    if not embeddings:
        return np.array([]).reshape(0, 3)

    embeddings_array = np.array(embeddings)

    if method.lower() == 'umap':
        reducer = umap.UMAP(n_components=3, random_state=42, n_neighbors=15, min_dist=0.1)
    elif method.lower() == 'tsne':
        reducer = TSNE(n_components=3, random_state=42, perplexity=min(30, len(embeddings)-1))
    else:
        raise ValueError(f"Unknown method: {method}. Use 'umap' or 'tsne'")

    return reducer.fit_transform(embeddings_array)


def create_2d_embedding_plot(
    embeddings: List[List[float]],
    labels: Optional[List[str]] = None,
    similarities: Optional[List[float]] = None,
    query_embedding: Optional[List[float]] = None,
    method: str = 'umap',
    title: str = 'Embedding Space (2D Projection)'
) -> go.Figure:
    """Create interactive 2D embedding space plot.

    Args:
        embeddings: List of document chunk embeddings
        labels: Optional labels for each point (e.g., document names)
        similarities: Optional similarity scores for coloring
        query_embedding: Optional query embedding to highlight
        method: Projection method ('umap' or 'tsne')
        title: Plot title

    Returns:
        Plotly figure object
    """
    coords_2d = project_embeddings_2d(embeddings, method)

    if not labels:
        labels = [f"Chunk {i+1}" for i in range(len(embeddings))]

    # Color by similarity if provided
    if similarities:
        colors = similarities
        colorbar_title = "Similarity"
        colorscale = 'RdYlBu_r'  # Red for low, blue for high
    else:
        colors = 'blue'
        colorbar_title = None
        colorscale = None

    fig = go.Figure()

    # Add document embeddings
    fig.add_trace(go.Scatter(
        x=coords_2d[:, 0],
        y=coords_2d[:, 1],
        mode='markers',
        marker=dict(
            size=8,
            color=colors,
            colorscale=colorscale,
            colorbar=dict(title=colorbar_title) if colorbar_title else None,
            showscale=bool(similarities)
        ),
        text=labels,
        hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}' +
                      ('<br>Similarity: %{marker.color:.3f}' if similarities else '') +
                      '<extra></extra>',
        name='Documents'
    ))

    # Add query embedding if provided
    if query_embedding:
        query_coords = project_embeddings_2d([query_embedding], method)
        fig.add_trace(go.Scatter(
            x=query_coords[:, 0],
            y=query_coords[:, 1],
            mode='markers',
            marker=dict(size=12, color='red', symbol='star'),
            text=['Query'],
            hovertemplate='<b>Query</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<extra></extra>',
            name='Query'
        ))

    fig.update_layout(
        title=title,
        xaxis_title=f'{method.upper()} Dimension 1',
        yaxis_title=f'{method.upper()} Dimension 2',
        hovermode='closest'
    )

    return fig


def create_3d_embedding_plot(
    embeddings: List[List[float]],
    labels: Optional[List[str]] = None,
    similarities: Optional[List[float]] = None,
    query_embedding: Optional[List[float]] = None,
    method: str = 'umap',
    title: str = 'Embedding Space (3D Projection)'
) -> go.Figure:
    """Create interactive 3D embedding space plot.

    Args:
        embeddings: List of document chunk embeddings
        labels: Optional labels for each point
        similarities: Optional similarity scores for coloring
        query_embedding: Optional query embedding to highlight
        method: Projection method ('umap' or 'tsne')
        title: Plot title

    Returns:
        Plotly figure object
    """
    coords_3d = project_embeddings_3d(embeddings, method)

    if not labels:
        labels = [f"Chunk {i+1}" for i in range(len(embeddings))]

    # Color by similarity if provided
    if similarities:
        colors = similarities
        colorbar_title = "Similarity"
        colorscale = 'RdYlBu_r'
    else:
        colors = 'blue'
        colorbar_title = None
        colorscale = None

    fig = go.Figure()

    # Add document embeddings
    fig.add_trace(go.Scatter3d(
        x=coords_3d[:, 0],
        y=coords_3d[:, 1],
        z=coords_3d[:, 2],
        mode='markers',
        marker=dict(
            size=6,
            color=colors,
            colorscale=colorscale,
            colorbar=dict(title=colorbar_title) if colorbar_title else None,
            showscale=bool(similarities)
        ),
        text=labels,
        hovertemplate='<b>%{text}</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}' +
                      ('<br>Similarity: %{marker.color:.3f}' if similarities else '') +
                      '<extra></extra>',
        name='Documents'
    ))

    # Add query embedding if provided
    if query_embedding:
        query_coords = project_embeddings_3d([query_embedding], method)
        fig.add_trace(go.Scatter3d(
            x=query_coords[:, 0],
            y=query_coords[:, 1],
            z=query_coords[:, 2],
            mode='markers',
            marker=dict(size=10, color='red', symbol='diamond'),
            text=['Query'],
            hovertemplate='<b>Query</b><br>X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<extra></extra>',
            name='Query'
        ))

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title=f'{method.upper()} Dim 1',
            yaxis_title=f'{method.upper()} Dim 2',
            zaxis_title=f'{method.upper()} Dim 3'
        ),
        hovermode='closest'
    )

    return fig


def get_embeddings_for_visualization(query_id: Optional[str] = None, config: Optional[dict] = None) -> Tuple[List[List[float]], List[str], Optional[List[float]]]:
    """Get embeddings and labels for visualization from recent query or all documents.

    Args:
        query_id: Optional query ID to get relevant embeddings
        config: Configuration dictionary

    Returns:
        Tuple of (embeddings, labels, similarities)
    """
    # TODO: Implement database queries to get embeddings
    # For now, return empty - this would need database access
    if config is None:
        config = load_config()

    # Placeholder - would need to query chunks table
    embeddings = []
    labels = []
    similarities = None

    return embeddings, labels, similarities
