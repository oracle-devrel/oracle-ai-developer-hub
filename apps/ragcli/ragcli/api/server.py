"""FastAPI server for ragcli - AnythingLLM integration."""

import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from ragcli.config.config_manager import load_config
from ragcli.core.rag_engine import upload_document, ask_query
from ragcli.core.ollama_manager import (
    list_available_models,
    get_model_info,
    validate_model
)
from ragcli.database.oracle_client import OracleClient
from ragcli.utils.status import get_overall_status, get_document_stats
from ragcli.utils.validators import sanitize_filename
from ragcli.utils.logger import get_logger
from .models import (
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    QueryRequest,
    QueryResponse,
    ChunkResult,
    ModelsResponse,
    OllamaModel,
    SystemStatus,
    SystemStats,
    ComponentStatus,
    GraphNode,
    GraphEdge,
    GraphMetadata,
    EmbeddingGraphResponse,
    GraphQueryRequest,
    FeedbackRequest,
    FeedbackStatsResponse,
    EvalRunRequest,
    EvalRunResponse,
    EvalRunListResponse,
    SyncSourceRequest,
    SyncSourceResponse,
    SyncSourceListResponse,
    SyncEventResponse,
    SyncEventListResponse,
    SessionResponse,
    SessionListResponse,
    SessionTurnResponse,
    SessionTurnListResponse,
)
from ragcli.database.vector_ops import get_embedding_graph, get_query_graph
from ragcli.core.embedding import generate_embedding
from ragcli.feedback.collector import FeedbackCollector
from ragcli.feedback.analyzer import FeedbackAnalyzer
from ragcli.eval.runner import EvalRunner
from ragcli.sync.scheduler import SyncScheduler
from ragcli.memory.session import SessionManager

logger = get_logger(__name__)

# Load config
config = load_config()

# Singleton connection pool — created once at startup, shared across requests
_db_client: Optional[OracleClient] = None

def get_db_client() -> OracleClient:
    """Get or create the singleton OracleClient."""
    global _db_client
    if _db_client is None:
        _db_client = OracleClient(config)
    return _db_client

# Create FastAPI app
app = FastAPI(
    title="ragcli API",
    description="REST API for RAG operations with Oracle 26ai and Ollama",
    version="1.0.0",
    docs_url="/docs" if config.get('api', {}).get('enable_swagger', True) else None
)

# CORS middleware — only enable credentials when origins are explicitly specified
cors_origins = config.get('api', {}).get('cors_origins', ["*"])
allow_credentials = "*" not in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connection pool on shutdown."""
    global _db_client
    if _db_client is not None:
        _db_client.close()
        _db_client = None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ragcli API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document_endpoint(file: UploadFile = File(...)):
    """
    Upload and process a document.

    Supported formats: TXT, MD, PDF
    """
    try:
        # Sanitize the uploaded filename
        safe_filename = sanitize_filename(file.filename or "upload")

        # Save uploaded file to temp location
        suffix = os.path.splitext(safe_filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Process document
        try:
            result = upload_document(tmp_path, config)

            return DocumentUploadResponse(
                document_id=result['document_id'],
                filename=result['filename'],
                file_format=result['file_format'],
                file_size_bytes=result['file_size_bytes'],
                chunk_count=result['chunk_count'],
                total_tokens=result['total_tokens'],
                upload_time_ms=result['upload_time_ms']
            )
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed. Check server logs for details.")


@app.get("/api/documents", response_model=DocumentListResponse)
async def list_documents(
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: Optional[int] = Query(0, ge=0)
):
    """List all documents with metadata."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        with conn.cursor() as cursor:
            # Get documents with pagination
            cursor.execute("""
                SELECT document_id, filename, file_format, file_size_bytes,
                       chunk_count, total_tokens, upload_timestamp, last_modified
                FROM DOCUMENTS
                ORDER BY upload_timestamp DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """, {"offset": offset, "limit": limit})

            rows = cursor.fetchall()

            # Get total count
            cursor.execute("SELECT COUNT(*) FROM DOCUMENTS")
            total_count = cursor.fetchone()[0]

        documents = [
            DocumentInfo(
                document_id=row[0],
                filename=row[1],
                file_format=row[2],
                file_size_bytes=row[3],
                chunk_count=row[4],
                total_tokens=row[5],
                upload_timestamp=row[6],
                last_modified=row[7]
            )
            for row in rows
        ]

        return DocumentListResponse(
            documents=documents,
            total_count=total_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list documents. Check server logs for details.")
    finally:
        conn.close()


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if document exists
            cursor.execute("SELECT filename FROM DOCUMENTS WHERE document_id = :doc_id", {"doc_id": doc_id})
            result = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Document not found")

            filename = result[0]

            # Delete chunks first (foreign key constraint)
            cursor.execute("DELETE FROM CHUNKS WHERE document_id = :doc_id", {"doc_id": doc_id})
            chunks_deleted = cursor.rowcount

            # Delete document
            cursor.execute("DELETE FROM DOCUMENTS WHERE document_id = :doc_id", {"doc_id": doc_id})

        conn.commit()

        return {
            "message": f"Document '{filename}' deleted successfully",
            "document_id": doc_id,
            "chunks_deleted": chunks_deleted
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document. Check server logs for details.")
    finally:
        conn.close()


@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Perform RAG query.

    Retrieves relevant document chunks and generates response using LLM.
    """
    try:
        result = ask_query(
            query=request.query,
            document_ids=request.document_ids,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            config=config,
            stream=False,
            include_embeddings=request.include_embeddings,
            session_id=request.session_id,
        )

        chunks = [
            ChunkResult(
                chunk_id=chunk['chunk_id'],
                document_id=chunk['document_id'],
                text=chunk['text'],
                similarity_score=chunk['similarity_score'],
                chunk_number=chunk['chunk_number'],
                embedding=chunk.get('embedding') if request.include_embeddings else None
            )
            for chunk in result['results']
        ]

        return QueryResponse(
            response=result['response'],
            chunks=chunks,
            query_embedding=result.get('query_embedding'),
            metrics=result['metrics'],
            session_id=result.get('session_id'),
            trace_id=result.get('trace_id'),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Query failed. Check server logs for details.")


@app.get("/api/models", response_model=ModelsResponse)
async def list_models():
    """List available Ollama models (embedding and chat)."""
    try:
        models = list_available_models(config)

        embedding_models = []
        chat_models = []

        for model in models.get('models', []):
            model_obj = OllamaModel(
                name=model['name'],
                size=model.get('size', 0),
                modified_at=model.get('modified_at', ''),
                family=model.get('details', {}).get('family'),
                parameter_size=model.get('details', {}).get('parameter_size')
            )

            # Categorize models (simple heuristic)
            if 'embed' in model['name'].lower():
                embedding_models.append(model_obj)
            else:
                chat_models.append(model_obj)

        return ModelsResponse(
            embedding_models=embedding_models,
            chat_models=chat_models,
            current_embedding_model=config['ollama']['embedding_model'],
            current_chat_model=config['ollama']['chat_model']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list models. Check server logs for details.")


@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get system health status."""
    try:
        status = get_overall_status(config)

        return SystemStatus(
            healthy=status['healthy'],
            database=ComponentStatus(
                status=status['database']['status'],
                message=status['database']['message']
            ),
            ollama=ComponentStatus(
                status=status['ollama']['status'],
                message=status['ollama']['message']
            ),
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get status. Check server logs for details.")


@app.get("/api/stats", response_model=SystemStats)
async def get_stats():
    """Get system statistics."""
    try:
        doc_stats = get_document_stats(config)

        # Get vector dimension from config
        dimension = config.get('vector_index', {}).get('dimension', 768)
        index_type = config.get('vector_index', {}).get('index_type', 'HNSW')

        return SystemStats(
            total_documents=doc_stats['documents'],
            total_vectors=doc_stats['vectors'],
            total_tokens=doc_stats['total_tokens'],
            embedding_dimension=dimension,
            index_type=index_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get stats. Check server logs for details.")


@app.get("/api/embeddings/graph", response_model=EmbeddingGraphResponse)
async def get_graph(
    min_similarity: float = Query(0.5, ge=0.0, le=1.0),
    top_k: int = Query(10, ge=1, le=50),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    limit: int = Query(500, ge=1, le=5000)
):
    """Get embedding similarity graph for visualization."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        doc_id_list = document_ids.split(",") if document_ids else None

        result = get_embedding_graph(
            conn=conn,
            min_similarity=min_similarity,
            top_k=top_k,
            document_ids=doc_id_list,
            limit=limit
        )

        nodes = [GraphNode(**n) for n in result["nodes"]]
        edges = [GraphEdge(**e) for e in result["edges"]]

        return EmbeddingGraphResponse(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                total_chunks=result["total_chunks"],
                returned_chunks=len(nodes),
                embedding_model=config['ollama']['embedding_model'],
                dimension=config.get('vector_index', {}).get('dimension', 768),
                min_similarity=min_similarity,
                top_k=top_k
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to build graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to build graph. Check server logs for details.")
    finally:
        conn.close()


@app.post("/api/embeddings/graph/query", response_model=EmbeddingGraphResponse)
async def get_query_graph_endpoint(request: GraphQueryRequest):
    """Get embedding graph with a query node included."""
    embedding_model = config['ollama']['embedding_model']
    query_embedding = generate_embedding(request.query, embedding_model, config)

    client = get_db_client()
    conn = client.get_connection()
    try:
        result = get_query_graph(
            conn=conn,
            query_embedding=query_embedding,
            query_text=request.query,
            min_similarity=request.min_similarity,
            top_k=request.top_k,
            document_ids=request.document_ids,
            limit=request.limit
        )

        nodes = [GraphNode(**n) for n in result["nodes"]]
        edges = [GraphEdge(**e) for e in result["edges"]]

        return EmbeddingGraphResponse(
            nodes=nodes,
            edges=edges,
            metadata=GraphMetadata(
                total_chunks=result["total_chunks"],
                returned_chunks=len(nodes),
                embedding_model=embedding_model,
                dimension=config.get('vector_index', {}).get('dimension', 768),
                min_similarity=request.min_similarity,
                top_k=request.top_k
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to build query graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to build query graph. Check server logs for details.")
    finally:
        conn.close()


# --- Feedback Endpoints ---

@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit answer or chunk feedback."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        collector = FeedbackCollector(conn)
        if request.target_type == "answer":
            collector.submit_answer_feedback(request.query_id, request.rating, request.comment)
        elif request.target_type == "chunk":
            collector.submit_chunk_feedback(request.query_id, request.chunk_id, request.rating, request.comment)
        else:
            raise HTTPException(status_code=400, detail="target_type must be 'answer' or 'chunk'")
        return {"message": "Feedback submitted", "target_type": request.target_type}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit feedback.")
    finally:
        conn.close()


@app.get("/api/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats():
    """Get feedback statistics."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        collector = FeedbackCollector(conn)
        stats = collector.get_feedback_stats()
        return FeedbackStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get feedback stats.")
    finally:
        conn.close()


# --- Eval Endpoints ---

@app.post("/api/eval/run", response_model=EvalRunResponse)
async def trigger_eval_run(request: EvalRunRequest):
    """Trigger an evaluation run."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        runner = EvalRunner(conn, config)
        run_id = runner.create_run(request.eval_mode)
        run_data = runner.get_run(run_id)
        return EvalRunResponse(
            run_id=run_data['run_id'],
            eval_mode=run_data['eval_mode'],
            started_at=run_data.get('started_at'),
            total_pairs=run_data.get('total_pairs', 0)
        )
    except Exception as e:
        logger.error(f"Failed to trigger eval run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger eval run.")
    finally:
        conn.close()


@app.get("/api/eval/runs", response_model=EvalRunListResponse)
async def list_eval_runs():
    """List evaluation runs."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        runner = EvalRunner(conn, config)
        runs = runner.list_runs()
        return EvalRunListResponse(
            runs=[EvalRunResponse(
                run_id=r['run_id'],
                eval_mode=r['eval_mode'],
                started_at=r.get('started_at'),
                completed_at=r.get('completed_at'),
                avg_faithfulness=r.get('avg_faithfulness'),
                avg_relevance=r.get('avg_relevance'),
                avg_context_precision=r.get('avg_context_precision'),
                avg_context_recall=r.get('avg_context_recall'),
                total_pairs=r.get('total_pairs', 0)
            ) for r in runs]
        )
    except Exception as e:
        logger.error(f"Failed to list eval runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list eval runs.")
    finally:
        conn.close()


@app.get("/api/eval/runs/{run_id}")
async def get_eval_run(run_id: str):
    """Get evaluation run details with results."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        runner = EvalRunner(conn, config)
        run_data = runner.get_run(run_id)
        if not run_data:
            raise HTTPException(status_code=404, detail="Eval run not found")
        results = runner.get_run_results(run_id)
        return {"run": run_data, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get eval run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get eval run.")
    finally:
        conn.close()


# --- Sync Endpoints ---

@app.post("/api/sync/sources", response_model=SyncSourceResponse)
async def add_sync_source(request: SyncSourceRequest):
    """Add a sync source."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        scheduler = SyncScheduler(conn, config.get('sync', {}))
        source_id = scheduler.add_source(
            source_type=request.source_type,
            path=request.path,
            glob_pattern=request.glob_pattern,
            poll_interval=request.poll_interval
        )
        source = scheduler.get_source(source_id)
        return SyncSourceResponse(
            source_id=source['source_id'],
            source_type=source['source_type'],
            source_path=source['source_path'],
            glob_pattern=source.get('glob_pattern'),
            poll_interval=source.get('poll_interval', 300),
            enabled=bool(source.get('enabled', 1)),
        )
    except Exception as e:
        logger.error(f"Failed to add sync source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to add sync source.")
    finally:
        conn.close()


@app.get("/api/sync/sources", response_model=SyncSourceListResponse)
async def list_sync_sources():
    """List sync sources."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        scheduler = SyncScheduler(conn, config.get('sync', {}))
        sources = scheduler.list_sources()
        return SyncSourceListResponse(
            sources=[SyncSourceResponse(
                source_id=s['source_id'],
                source_type=s['source_type'],
                source_path=s['source_path'],
                glob_pattern=s.get('glob_pattern'),
                poll_interval=s.get('poll_interval', 300),
                enabled=bool(s.get('enabled', 1)),
                last_sync=s.get('last_sync'),
            ) for s in sources]
        )
    except Exception as e:
        logger.error(f"Failed to list sync sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sync sources.")
    finally:
        conn.close()


@app.delete("/api/sync/sources/{source_id}")
async def remove_sync_source(source_id: str):
    """Remove a sync source."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        scheduler = SyncScheduler(conn, config.get('sync', {}))
        scheduler.remove_source(source_id)
        return {"message": "Sync source removed", "source_id": source_id}
    except Exception as e:
        logger.error(f"Failed to remove sync source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to remove sync source.")
    finally:
        conn.close()


@app.get("/api/sync/events", response_model=SyncEventListResponse)
async def list_sync_events(limit: int = Query(50, ge=1, le=500)):
    """List recent sync events."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        scheduler = SyncScheduler(conn, config.get('sync', {}))
        events = scheduler.get_recent_events(limit=limit)
        return SyncEventListResponse(
            events=[SyncEventResponse(
                event_id=e['event_id'],
                source_id=e['source_id'],
                file_path=e['file_path'],
                event_type=e['event_type'],
                document_id=e.get('document_id'),
                chunks_added=e.get('chunks_added', 0),
                chunks_removed=e.get('chunks_removed', 0),
                chunks_unchanged=e.get('chunks_unchanged', 0),
                processed_at=e.get('processed_at'),
            ) for e in events]
        )
    except Exception as e:
        logger.error(f"Failed to list sync events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sync events.")
    finally:
        conn.close()


# --- Session Endpoints ---

@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions():
    """List all sessions."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        session_mgr = SessionManager(conn)
        sessions = session_mgr.list_sessions()
        return SessionListResponse(
            sessions=[SessionResponse(
                session_id=s['session_id'],
                created_at=s.get('created_at'),
                last_active=s.get('last_active'),
                title=s.get('title'),
                summary=s.get('summary'),
            ) for s in sessions]
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sessions.")
    finally:
        conn.close()


@app.get("/api/sessions/{session_id}/turns", response_model=SessionTurnListResponse)
async def get_session_turns(session_id: str, limit: int = Query(50, ge=1, le=500)):
    """Get turns for a session."""
    client = get_db_client()
    conn = client.get_connection()
    try:
        session_mgr = SessionManager(conn)
        turns = session_mgr.get_recent_turns(session_id, limit=limit)
        return SessionTurnListResponse(
            turns=[SessionTurnResponse(
                turn_id=t.get('turn_id', ''),
                turn_number=t.get('turn_number', 0),
                user_query=t.get('user_query', ''),
                rewritten_query=t.get('rewritten_query'),
                response_text=t.get('response', ''),
                created_at=t.get('created_at'),
            ) for t in turns]
        )
    except Exception as e:
        logger.error(f"Failed to get session turns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session turns.")
    finally:
        conn.close()


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the FastAPI server."""
    uvicorn.run(
        "ragcli.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()
