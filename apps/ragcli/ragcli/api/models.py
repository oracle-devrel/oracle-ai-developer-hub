"""Pydantic models for ragcli API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    chunk_count: int
    total_tokens: int
    upload_time_ms: float
    message: str = "Document uploaded successfully"


class DocumentInfo(BaseModel):
    """Document metadata."""
    document_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    chunk_count: int
    total_tokens: int
    upload_timestamp: datetime
    last_modified: datetime


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    documents: List[DocumentInfo]
    total_count: int


class QueryRequest(BaseModel):
    """Request for RAG query."""
    query: str = Field(..., min_length=1, description="The question to ask")
    document_ids: Optional[List[str]] = Field(None, description="Filter by specific document IDs")
    top_k: Optional[int] = Field(5, ge=1, le=50, description="Number of chunks to retrieve")
    min_similarity: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    stream: bool = Field(False, description="Enable streaming response")
    include_embeddings: bool = Field(False, description="Include vector embeddings in response")
    session_id: Optional[str] = Field(None, description="Session ID for conversational RAG")


class ChunkResult(BaseModel):
    """Retrieved chunk information."""
    chunk_id: str
    document_id: str
    text: str
    similarity_score: float
    chunk_number: int
    embedding: Optional[List[float]] = None


class QueryResponse(BaseModel):
    """Response for RAG query."""
    response: str
    chunks: List[ChunkResult]
    query_embedding: Optional[List[float]] = None
    metrics: Dict[str, Any]
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


class OllamaModel(BaseModel):
    """Ollama model information."""
    name: str
    size: int
    modified_at: str
    family: Optional[str] = None
    parameter_size: Optional[str] = None


class ModelsResponse(BaseModel):
    """Response for listing models."""
    embedding_models: List[OllamaModel]
    chat_models: List[OllamaModel]
    current_embedding_model: str
    current_chat_model: str


class ComponentStatus(BaseModel):
    """Status of a system component."""
    status: str
    message: str


class SystemStatus(BaseModel):
    """Overall system status."""
    healthy: bool
    database: ComponentStatus
    ollama: ComponentStatus
    timestamp: datetime


class SystemStats(BaseModel):
    """System statistics."""
    total_documents: int
    total_vectors: int
    total_tokens: int
    embedding_dimension: int
    index_type: Optional[str] = None


class GraphNode(BaseModel):
    """Node in the embedding graph."""
    id: str
    document_id: str
    document_name: str
    chunk_number: int
    text_preview: str
    token_count: int
    node_type: str = "chunk"  # "chunk" or "query"


class GraphEdge(BaseModel):
    """Edge in the embedding graph."""
    source: str
    target: str
    similarity: float


class GraphMetadata(BaseModel):
    """Metadata about the graph."""
    total_chunks: int
    returned_chunks: int
    embedding_model: str
    dimension: int
    min_similarity: float
    top_k: int


class EmbeddingGraphResponse(BaseModel):
    """Response for embedding graph endpoint."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: GraphMetadata


class GraphQueryRequest(BaseModel):
    """Request for graph with query node."""
    query: str = Field(..., min_length=1, description="Query text to embed and add as node")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0)
    top_k: int = Field(10, ge=1, le=50)
    document_ids: Optional[List[str]] = None
    limit: int = Field(500, ge=1, le=5000)


# --- Feedback Models ---

class FeedbackRequest(BaseModel):
    """Request to submit feedback."""
    query_id: Optional[str] = None
    chunk_id: Optional[str] = None
    target_type: str = Field(..., description="'answer' or 'chunk'")
    rating: int = Field(..., ge=-1, le=1, description="-1, 0, or +1")
    comment: Optional[str] = None


class FeedbackStatsResponse(BaseModel):
    """Feedback statistics."""
    total_feedback: int
    avg_rating: float
    total_chunk_feedback: int
    total_answer_feedback: int


# --- Eval Models ---

class EvalRunRequest(BaseModel):
    """Request to trigger an eval run."""
    eval_mode: str = Field("synthetic", description="synthetic, replay, or live")
    document_id: Optional[str] = None


class EvalRunResponse(BaseModel):
    """Eval run summary."""
    run_id: str
    eval_mode: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    avg_faithfulness: Optional[float] = None
    avg_relevance: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_context_recall: Optional[float] = None
    total_pairs: int = 0


class EvalRunListResponse(BaseModel):
    """List of eval runs."""
    runs: List[EvalRunResponse]


# --- Sync Models ---

class SyncSourceRequest(BaseModel):
    """Request to add a sync source."""
    source_type: str = Field(..., description="directory, git, or url")
    path: str = Field(..., description="Path or URL to sync")
    glob_pattern: Optional[str] = None
    poll_interval: Optional[int] = Field(300, ge=10)


class SyncSourceResponse(BaseModel):
    """Sync source info."""
    source_id: str
    source_type: str
    source_path: str
    glob_pattern: Optional[str] = None
    poll_interval: int = 300
    enabled: bool = True
    last_sync: Optional[datetime] = None


class SyncSourceListResponse(BaseModel):
    """List of sync sources."""
    sources: List[SyncSourceResponse]


class SyncEventResponse(BaseModel):
    """Sync event info."""
    event_id: str
    source_id: str
    file_path: str
    event_type: str
    document_id: Optional[str] = None
    chunks_added: int = 0
    chunks_removed: int = 0
    chunks_unchanged: int = 0
    processed_at: Optional[datetime] = None


class SyncEventListResponse(BaseModel):
    """List of sync events."""
    events: List[SyncEventResponse]


# --- Session Models ---

class SessionResponse(BaseModel):
    """Session info."""
    session_id: str
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of sessions."""
    sessions: List[SessionResponse]


class SessionTurnResponse(BaseModel):
    """Session turn info."""
    turn_id: str
    turn_number: int
    user_query: str
    rewritten_query: Optional[str] = None
    response_text: Optional[str] = None
    created_at: Optional[datetime] = None


class SessionTurnListResponse(BaseModel):
    """List of session turns."""
    turns: List[SessionTurnResponse]
