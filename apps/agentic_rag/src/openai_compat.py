"""
OpenAI-compatible API layer for Open WebUI integration.

This module provides /v1/models and /v1/chat/completions endpoints
that are compatible with the OpenAI API specification, allowing
Open WebUI and other OpenAI-compatible clients to consume our
reasoning and RAG capabilities.

Now uses ReasoningInterceptor directly (like CLI arena mode) for
full multi-step streaming output from reasoning agents with real-time
chunk-by-chunk streaming.
"""

import json
import time
import uuid
import asyncio
import re
import queue
import threading
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# Import ReasoningInterceptor for direct Ollama-like streaming
try:
    from agent_reasoning import ReasoningInterceptor
    INTERCEPTOR_AVAILABLE = True
except ImportError:
    INTERCEPTOR_AVAILABLE = False
    print("⚠️ ReasoningInterceptor not available, falling back to ensemble mode", flush=True)


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def log_a2a_event(method: str, status: str, details: str = "", **kwargs):
    """
    Log A2A-style events to stdout (visible in server logs).
    Mimics the logging format used in gradio_app.py.
    Forces flush to ensure logs appear immediately in buffered server contexts.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    icon = "✅" if status == "success" else "❌" if status == "error" else "🔄"

    extra = " | ".join([f"{k}: {v}" for k, v in kwargs.items() if v])
    if extra:
        extra = f" | {extra}"

    print(f"{icon} [{timestamp}] [A2A Event] Method: {method} | Status: {status}{extra}", flush=True)
    if details:
        print(f"   └─ {details}", flush=True)

from .openai_models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatMessage,
    DeltaContent,
    ModelList,
    ModelInfo,
    UsageInfo,
    ErrorResponse,
    ErrorDetail,
    ContentPart,
    FileAttachment,
    REASONING_MODELS,
    get_model_list,
    get_model_config,
)

# Import WebProcessor for URL fetching
try:
    from .web_processor import WebProcessor, is_url
except ImportError:
    try:
        from web_processor import WebProcessor, is_url
    except ImportError:
        WebProcessor = None
        is_url = lambda x: False
        print("⚠️ WebProcessor not available, Upload Link persistence disabled", flush=True)

# Router for OpenAI-compatible endpoints
router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])

# Global references to be set during initialization
_vector_store = None
_reasoning_ensemble = None
_local_agent = None
_config = {}
_interceptor = None  # ReasoningInterceptor for direct agent streaming
_event_logger = None  # Oracle DB event logger for tracking all events
_file_handler = None  # FileHandler for @file reference processing
_a2a_handler = None  # A2AHandler for routing through A2A protocol


def init_openai_compat(
    vector_store,
    reasoning_ensemble=None,
    local_agent=None,
    config: Optional[Dict[str, Any]] = None,
    event_logger=None,
    file_handler=None,
    a2a_handler=None
):
    """
    Initialize the OpenAI-compatible API with required dependencies.

    Args:
        vector_store: VectorStore or OraDBVectorStore instance
        reasoning_ensemble: RAGReasoningEnsemble instance (optional)
        local_agent: LocalRAGAgent instance for fallback (optional)
        config: Configuration dict (optional)
        event_logger: OraDBEventLogger instance for database logging (optional)
        file_handler: FileHandler instance for @file processing (optional)
        a2a_handler: A2AHandler instance for A2A protocol routing (optional)
    """
    global _vector_store, _reasoning_ensemble, _local_agent, _config, _interceptor, _event_logger, _file_handler, _a2a_handler
    _vector_store = vector_store
    _reasoning_ensemble = reasoning_ensemble
    _local_agent = local_agent
    _config = config or {}
    _event_logger = event_logger
    _file_handler = file_handler
    _a2a_handler = a2a_handler

    # Initialize ReasoningInterceptor for direct agent streaming (like CLI arena mode)
    if INTERCEPTOR_AVAILABLE:
        try:
            _interceptor = ReasoningInterceptor(host="http://localhost:11434")
            print("✅ ReasoningInterceptor initialized for direct agent streaming", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to initialize ReasoningInterceptor: {e}", flush=True)
            _interceptor = None


async def unified_rag_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search across all collections (PDF, Web, Repository) and return unified results.

    Args:
        query: Search query
        top_k: Maximum number of results to return

    Returns:
        List of document chunks with metadata, sorted by relevance
    """
    if not _vector_store:
        return []

    all_results = []
    search_start_time = time.time()

    # Query each collection
    collections = [
        ("pdf_documents", "query_pdf_collection"),
        ("web_documents", "query_web_collection"),
        ("repository_documents", "query_repo_collection"),
    ]

    for collection_name, method_name in collections:
        try:
            if hasattr(_vector_store, method_name):
                method = getattr(_vector_store, method_name)
                results = method(query, n_results=top_k)

                # Normalize results format
                if results:
                    for result in results:
                        if isinstance(result, dict):
                            result["collection"] = collection_name
                            all_results.append(result)
        except Exception as e:
            print(f"Error querying {collection_name}: {e}", flush=True)
            continue

    # Sort by score (if available) and take top_k
    def get_score(item):
        if isinstance(item, dict):
            # Try different score field names
            for key in ["score", "distance", "similarity"]:
                if key in item:
                    score = item[key]
                    # Invert distance scores (lower is better)
                    if key == "distance":
                        return -score
                    return score
        return 0

    all_results.sort(key=get_score, reverse=True)
    final_results = all_results[:top_k]

    # Log RAG query to Oracle DB
    if _event_logger and final_results:
        try:
            query_duration_ms = (time.time() - search_start_time) * 1000
            _event_logger.log_query_event(
                query_text=query[:500],  # Truncate for DB
                collection_name="unified_rag",
                results_count=len(final_results),
                query_time_ms=query_duration_ms,
                metadata={
                    "collections_searched": [c[0] for c in collections],
                    "top_k": top_k
                }
            )
        except Exception as e:
            print(f"[EventLogger] Error logging RAG query to Oracle DB: {e}", flush=True)

    return final_results


def build_rag_context(results: List[Dict[str, Any]]) -> str:
    """Build context string from RAG results."""
    if not results:
        return ""

    context_parts = ["Here is relevant context from the knowledge base:\n"]

    for i, result in enumerate(results, 1):
        content = result.get("content", result.get("text", ""))
        source = result.get("metadata", {}).get("source", result.get("collection", "Unknown"))

        context_parts.append(f"[{i}] Source: {source}")
        context_parts.append(f"{content}\n")

    context_parts.append("\nUse the above context to help answer the user's question.\n")
    return "\n".join(context_parts)


def format_rag_sources_for_display(results: List[Dict[str, Any]]) -> str:
    """
    Format RAG sources for visual display in Open WebUI.
    Returns a markdown-formatted string showing retrieved documents.
    """
    if not results:
        return ""

    lines = [
        "---",
        "📚 **Retrieved Knowledge Sources**",
        ""
    ]

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        content = result.get("content", result.get("text", ""))
        score = result.get("score")
        collection = result.get("collection", "unknown")

        # Extract source info
        source = metadata.get("source", metadata.get("url", metadata.get("file_path", "Unknown")))
        doc_type = metadata.get("type", collection.replace("_documents", "").upper())
        page = metadata.get("page", metadata.get("page_number"))
        chunk_id = metadata.get("chunk_id", metadata.get("id", ""))

        # Format score as percentage if available
        score_str = f" | Relevance: {score:.1%}" if score is not None else ""

        # Build source line
        source_line = f"**[{i}]** 📄 `{doc_type}`{score_str}"
        lines.append(source_line)

        # Add source path/URL
        if source and source != "Unknown":
            # Truncate long paths
            display_source = source if len(source) <= 60 else "..." + source[-57:]
            lines.append(f"   📍 Source: `{display_source}`")

        # Add page info if available
        if page:
            lines.append(f"   📑 Page: {page}")

        # Add content preview (first 150 chars)
        preview = content[:150].replace("\n", " ").strip()
        if len(content) > 150:
            preview += "..."
        lines.append(f"   > _{preview}_")
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


async def process_file_references(
    message: str
) -> tuple[str, str, List[Dict[str, Any]]]:
    """
    Process @file and @@file references in a message.

    Patterns:
    - @filename.ext → temporary context (inject into current query)
    - @@filename.ext → permanent storage (add to RAG, then inject)

    Args:
        message: The user message containing file references

    Returns:
        Tuple of (cleaned_message, file_context, file_display_info)
    """
    if not _file_handler:
        return message, "", []

    # Import the parser
    try:
        from .file_handler import parse_file_references
    except ImportError:
        from file_handler import parse_file_references

    cleaned_message, references = parse_file_references(message)

    if not references:
        return message, "", []

    file_context_parts = []
    file_display_info = []

    for ref in references:
        filepath = ref["filepath"]
        permanent = ref["permanent"]

        log_a2a_event(
            "file.reference",
            "processing",
            f"{'@@' if permanent else '@'}{filepath}",
            permanent=permanent
        )

        # Find the file
        found_path = _file_handler.find_file(filepath)

        if not found_path:
            log_a2a_event("file.reference", "error", f"File not found: {filepath}")
            file_display_info.append({
                "filename": filepath,
                "status": "not_found",
                "error": "File not found"
            })
            continue

        try:
            if permanent:
                # Add to RAG and inject context
                result = _file_handler.add_to_rag(found_path, "GENERALCOLLECTION")
                log_a2a_event(
                    "file.reference",
                    "success",
                    f"Added to RAG: {filepath}",
                    chunks=result.get("chunks_stored", 0)
                )
            else:
                # Just process for temporary context
                result = _file_handler.add_temporary(found_path)
                log_a2a_event(
                    "file.reference",
                    "success",
                    f"Temporary context: {filepath}",
                    chunks=len(result.get("chunks", []))
                )

            # Build context from file content
            content = result.get("content", "")
            if content:
                file_context_parts.append(
                    f"--- Content from {filepath} ---\n{content}\n--- End of {filepath} ---"
                )

            file_display_info.append({
                "filename": found_path.name,
                "path": str(found_path),
                "status": "success",
                "storage_mode": "permanent" if permanent else "temporary",
                "chunks": len(result.get("chunks", [])),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            })

        except Exception as e:
            log_a2a_event("file.reference", "error", f"Failed to process {filepath}: {e}")
            file_display_info.append({
                "filename": filepath,
                "status": "error",
                "error": str(e)
            })

    # Combine file contexts
    file_context = "\n\n".join(file_context_parts) if file_context_parts else ""

    return cleaned_message, file_context, file_display_info


def format_file_references_for_display(file_info: List[Dict[str, Any]]) -> str:
    """
    Format file references for visual display in Open WebUI.
    """
    if not file_info:
        return ""

    lines = [
        "---",
        "📎 **Referenced Files**",
        ""
    ]

    for f in file_info:
        status_icon = "✅" if f["status"] == "success" else "❌"
        mode_icon = "💾" if f.get("storage_mode") == "permanent" else "📎"

        if f["status"] == "success":
            lines.append(f"{status_icon} {mode_icon} **{f['filename']}**")
            if f.get("chunks"):
                lines.append(f"   └─ {f['chunks']} chunks processed")
        else:
            lines.append(f"{status_icon} **{f['filename']}**: {f.get('error', 'Unknown error')}")

        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


@router.get("/models", response_model=ModelList)
async def list_models():
    """
    List available models (reasoning strategies).

    OpenAI-compatible endpoint that returns the list of available
    "models" which map to reasoning strategies in our system.
    """
    return get_model_list()


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """Get information about a specific model."""
    config = get_model_config(model_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail={"error": {"message": f"Model '{model_id}' not found", "type": "invalid_request_error", "code": "model_not_found"}}
        )

    return ModelInfo(
        id=model_id,
        name=config["name"],
        description=config.get("description")
    )


async def run_interceptor_streaming(
    model_name: str,
    query: str,
    strategy: str
) -> AsyncGenerator[str, None]:
    """
    Run the ReasoningInterceptor in a thread with REAL-TIME streaming.

    Uses a queue to communicate between the blocking interceptor thread
    and the async generator, enabling true chunk-by-chunk streaming
    just like CLI arena mode.
    """
    # Queue for real-time chunk communication
    chunk_queue: queue.Queue = queue.Queue()
    SENTINEL = object()  # Marks end of stream
    thread_error = [None]  # Mutable container to capture thread errors

    def run_interceptor_thread():
        """Run interceptor in thread, pushing chunks to queue."""
        try:
            log_a2a_event(
                f"reasoning.{strategy}",
                "started",
                f"Model: {model_name}",
                query_preview=query[:50] + "..."
            )

            start_time = time.time()
            chunk_count = 0

            for chunk_dict in _interceptor.generate(
                model=model_name,
                prompt=query,
                stream=True
            ):
                chunk_text = chunk_dict.get("response", "")
                if chunk_text:
                    # Log significant chunks (step markers, observations)
                    if "--- Step" in chunk_text:
                        log_a2a_event(f"reasoning.{strategy}", "step", chunk_text.strip()[:60])
                    elif "Observation:" in chunk_text:
                        log_a2a_event(f"reasoning.{strategy}", "observation", "Code execution result")
                    elif "FINAL ANSWER" in chunk_text:
                        log_a2a_event(f"reasoning.{strategy}", "complete", "Final answer found")

                    chunk_queue.put(chunk_text)
                    chunk_count += 1

            duration_ms = (time.time() - start_time) * 1000
            log_a2a_event(
                f"reasoning.{strategy}",
                "success",
                f"Completed in {duration_ms:.0f}ms",
                chunks=chunk_count
            )

        except Exception as e:
            log_a2a_event(f"reasoning.{strategy}", "error", str(e))
            thread_error[0] = e
            chunk_queue.put(f"\n\n❌ Error: {str(e)}")
        finally:
            chunk_queue.put(SENTINEL)

    # Start interceptor in background thread
    thread = threading.Thread(target=run_interceptor_thread, daemon=True)
    thread.start()

    # Yield chunks as they arrive (real-time streaming)
    # Increased timeout for complex reasoning strategies like decomposed/least-to-most
    max_idle_iterations = 2400  # ~120 seconds max idle time (2400 * 0.05s)
    idle_count = 0

    try:
        while True:
            try:
                # Non-blocking check with small timeout for async compatibility
                chunk = chunk_queue.get(timeout=0.05)
                idle_count = 0  # Reset on successful get
                if chunk is SENTINEL:
                    break
                yield chunk
            except queue.Empty:
                idle_count += 1
                if idle_count > max_idle_iterations:
                    log_a2a_event(f"reasoning.{strategy}", "timeout", "Stream idle timeout")
                    yield "\n\n⚠️ Stream timeout - no response received"
                    break
                # No chunk yet, yield control back to event loop
                await asyncio.sleep(0.01)
                continue
    finally:
        # Ensure thread cleanup
        thread.join(timeout=2.0)
        if thread.is_alive():
            log_a2a_event(f"reasoning.{strategy}", "warning", "Thread still running after timeout")


async def generate_streaming_response(
    request: ChatCompletionRequest,
    model_config: Dict[str, Any],
    rag_context: str = "",
    rag_results: Optional[List[Dict[str, Any]]] = None,
    file_display_info: Optional[List[Dict[str, Any]]] = None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming chat completion response with REAL-TIME streaming.

    Yields SSE-formatted chunks compatible with OpenAI's streaming format.

    Uses ReasoningInterceptor directly (like CLI arena mode) for full
    multi-step streaming output from reasoning agents. Chunks are streamed
    in real-time as they are generated, not buffered.

    When rag_results is provided, displays the retrieved sources visually
    before the main response.

    When file_display_info is provided, displays the referenced files
    before RAG sources.
    """
    import traceback
    from .settings import get_current_model

    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    strategy = model_config["strategy"]
    start_time = time.time()

    # Log request start
    log_a2a_event(
        "chat.completions",
        "started",
        f"Strategy: {strategy}",
        request_id=request_id,
        model=request.model
    )

    # Get the user's query (last user message)
    user_query = ""
    for msg in reversed(request.messages):
        if msg.role.value == "user" and msg.content:
            user_query = msg.content
            break

    if not user_query:
        log_a2a_event("chat.completions", "error", "No user message found")
        error_chunk = ChatCompletionChunk(
            id=request_id,
            created=created,
            model=request.model,
            choices=[ChatCompletionChunkChoice(
                index=0,
                delta=DeltaContent(content="Error: No user message found"),
                finish_reason="stop"
            )]
        )
        yield f"data: {error_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        return

    log_a2a_event(
        "chat.query",
        "received",
        f"Query: {user_query[:80]}{'...' if len(user_query) > 80 else ''}"
    )

    # Build augmented query with RAG context
    augmented_query = user_query
    if rag_context:
        log_a2a_event("rag.context", "applied", f"Context length: {len(rag_context)} chars")
        augmented_query = f"{rag_context}\n\nUser Question: {user_query}"

    # Track if we've sent the initial role chunk
    initial_sent = False

    # Stream file references first if available
    if file_display_info and len(file_display_info) > 0:
        file_refs_text = format_file_references_for_display(file_display_info)
        if file_refs_text:
            log_a2a_event("file.references", "displaying", f"{len(file_display_info)} files")

            # Send initial role chunk
            initial_chunk = ChatCompletionChunk(
                id=request_id,
                created=created,
                model=request.model,
                choices=[ChatCompletionChunkChoice(
                    index=0,
                    delta=DeltaContent(role="assistant"),
                    finish_reason=None
                )]
            )
            yield f"data: {initial_chunk.model_dump_json()}\n\n"
            initial_sent = True

            # Stream file references in chunks
            chunk_size = 80
            for i in range(0, len(file_refs_text), chunk_size):
                text_chunk = file_refs_text[i:i + chunk_size]
                content_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=text_chunk),
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                await asyncio.sleep(0.005)

    # Stream RAG sources if available (for visual display in UI)
    rag_sources_displayed = False
    if rag_results and len(rag_results) > 0:
        rag_sources_text = format_rag_sources_for_display(rag_results)
        if rag_sources_text:
            log_a2a_event("rag.sources", "displaying", f"{len(rag_results)} sources")

            # Send initial role chunk only if not already sent
            if not initial_sent:
                initial_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(role="assistant"),
                        finish_reason=None
                    )]
                )
                yield f"data: {initial_chunk.model_dump_json()}\n\n"
                initial_sent = True

            # Stream RAG sources in chunks for smooth display
            chunk_size = 80
            for i in range(0, len(rag_sources_text), chunk_size):
                text_chunk = rag_sources_text[i:i + chunk_size]
                content_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=text_chunk),
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                await asyncio.sleep(0.005)

            rag_sources_displayed = True

    # PRIORITY 1: Use ReasoningInterceptor directly (like CLI arena mode)
    # This provides full multi-step streaming output with real-time chunks
    if INTERCEPTOR_AVAILABLE and _interceptor:
        interceptor_started = False
        try:
            # Get current model from settings
            base_model = get_current_model()
            # Build model name in interceptor format: base_model+strategy
            interceptor_model = f"{base_model}+{strategy}"

            # Log A2A event for reasoning request START
            if _a2a_handler and _a2a_handler.event_logger:
                _a2a_handler.event_logger.log_a2a_event(
                    agent_id=f"reasoning_{strategy}_v1",
                    agent_name=f"Reasoning Agent ({strategy})",
                    method="reasoning.stream",
                    user_prompt=user_query[:500],
                    response="[streaming started]",
                    metadata={
                        "request_id": request_id,
                        "model": interceptor_model,
                        "strategy": strategy,
                        "use_rag": bool(rag_context),
                        "source": "openai_compat"
                    },
                    duration_ms=0,
                    status="started"
                )

            log_a2a_event(
                "reasoning.dispatch",
                "started",
                f"Using ReasoningInterceptor",
                model=interceptor_model,
                strategy=strategy
            )

            # Send initial role chunk only if not already sent
            if not initial_sent:
                initial_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(role="assistant"),
                        finish_reason=None
                    )]
                )
                yield f"data: {initial_chunk.model_dump_json()}\n\n"
            else:
                # Add a separator between file refs/RAG sources and reasoning response
                separator = "\n\n🤖 **Agent Response**\n\n"
                sep_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=separator),
                        finish_reason=None
                    )]
                )
                yield f"data: {sep_chunk.model_dump_json()}\n\n"

            interceptor_started = True

            # Stream directly from interceptor (like CLI arena mode) - REAL-TIME
            full_response = ""
            start_time = time.time()

            async for chunk in run_interceptor_streaming(interceptor_model, augmented_query, strategy):
                # Clean ANSI codes from each chunk
                clean_chunk = strip_ansi_codes(chunk)
                full_response += clean_chunk

                # Stream each chunk as SSE immediately (real-time)
                content_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=clean_chunk),
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"

            duration_ms = (time.time() - start_time) * 1000
            log_a2a_event(
                "chat.completions",
                "success",
                f"Response complete",
                duration_ms=f"{duration_ms:.0f}",
                response_length=len(full_response)
            )

            # Log to Oracle DB
            if _event_logger:
                try:
                    # Log API event
                    _event_logger.log_api_event(
                        endpoint="/v1/chat/completions",
                        method="POST",
                        request_data={
                            "model": request.model,
                            "strategy": strategy,
                            "stream": True,
                            "query_preview": user_query[:100]
                        },
                        response_data={
                            "request_id": request_id,
                            "response_length": len(full_response),
                            "status": "success"
                        },
                        status_code=200,
                        duration_ms=duration_ms
                    )
                    # Log model event
                    _event_logger.log_model_event(
                        model_name=interceptor_model,
                        model_type="reasoning_interceptor",
                        user_prompt=user_query,
                        response=full_response[:2000],  # Truncate for DB
                        collection_used="unified_rag" if rag_context else None,
                        use_cot=strategy in ["cot", "tot", "react"],
                        duration_ms=duration_ms
                    )
                except Exception as e:
                    print(f"[EventLogger] Error logging to Oracle DB: {e}", flush=True)

            # Log A2A event for reasoning request COMPLETION
            if _a2a_handler and _a2a_handler.event_logger:
                try:
                    _a2a_handler.event_logger.log_a2a_event(
                        agent_id=f"reasoning_{strategy}_v1",
                        agent_name=f"Reasoning Agent ({strategy})",
                        method="reasoning.stream",
                        user_prompt=user_query[:500],
                        response=full_response[:2000],
                        metadata={
                            "request_id": request_id,
                            "model": interceptor_model,
                            "strategy": strategy,
                            "use_rag": bool(rag_context),
                            "response_length": len(full_response),
                            "source": "openai_compat"
                        },
                        duration_ms=duration_ms,
                        status="success"
                    )
                except Exception as e:
                    print(f"[A2A Event] Error logging A2A event: {e}", flush=True)

            # Send final chunk with finish_reason
            final_chunk = ChatCompletionChunk(
                id=request_id,
                created=created,
                model=request.model,
                choices=[ChatCompletionChunkChoice(
                    index=0,
                    delta=DeltaContent(),
                    finish_reason="stop"
                )]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            return

        except Exception as e:
            log_a2a_event("reasoning.dispatch", "error", str(e))
            traceback.print_exc()
            sys.stdout.flush()

            # If we already started streaming, we must properly terminate
            if interceptor_started:
                error_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=f"\n\n❌ Error: {str(e)}"),
                        finish_reason=None
                    )]
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                final_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(),
                        finish_reason="stop"
                    )]
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return
            # Fall through to ensemble fallback only if not started

    # FALLBACK 1: Use reasoning ensemble (non-streaming internally)
    if _reasoning_ensemble:
        ensemble_started = False
        try:
            log_a2a_event("reasoning.fallback", "started", "Using RAGReasoningEnsemble")

            # Send initial role chunk only if RAG sources weren't displayed
            if not initial_sent:
                initial_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(role="assistant"),
                        finish_reason=None
                    )]
                )
                yield f"data: {initial_chunk.model_dump_json()}\n\n"
            else:
                # Add separator
                separator = "\n\n🤖 **Agent Response**\n\n"
                sep_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=separator),
                        finish_reason=None
                    )]
                )
                yield f"data: {sep_chunk.model_dump_json()}\n\n"

            ensemble_started = True
            start_time = time.time()

            # Run the ensemble (non-streaming internally, we'll stream the result)
            result = await _reasoning_ensemble.run(
                query=augmented_query,
                strategies=[strategy],
                use_rag=False,  # We already did RAG above
                collection="General",
                config=None
            )

            # Get the response text and clean it
            response_text = result.winner.get("response", "No response generated")
            response_text = strip_ansi_codes(response_text)

            duration_ms = (time.time() - start_time) * 1000
            log_a2a_event(
                "reasoning.fallback",
                "success",
                f"Ensemble complete",
                duration_ms=f"{duration_ms:.0f}",
                response_length=len(response_text)
            )

            # Log to Oracle DB
            if _event_logger:
                try:
                    # Log API event
                    _event_logger.log_api_event(
                        endpoint="/v1/chat/completions",
                        method="POST",
                        request_data={
                            "model": request.model,
                            "strategy": strategy,
                            "stream": True,
                            "query_preview": user_query[:100]
                        },
                        response_data={
                            "request_id": request_id,
                            "response_length": len(response_text),
                            "status": "success",
                            "backend": "reasoning_ensemble"
                        },
                        status_code=200,
                        duration_ms=duration_ms
                    )
                    # Log reasoning event
                    _event_logger.log_reasoning_event(
                        query_text=user_query,
                        strategies_requested=[strategy],
                        winner_strategy=strategy,
                        winner_response=response_text[:2000],
                        vote_count=1,
                        all_responses=[{"strategy": strategy, "response": response_text[:500]}],
                        rag_enabled=bool(rag_context),
                        collection_used="unified_rag" if rag_context else None,
                        chunks_retrieved=0,
                        total_duration_ms=duration_ms,
                        status="success"
                    )
                except Exception as e:
                    print(f"[EventLogger] Error logging to Oracle DB: {e}", flush=True)

            # Stream the response in chunks
            chunk_size = 50  # Characters per chunk (larger for smoother display)
            for i in range(0, len(response_text), chunk_size):
                text_chunk = response_text[i:i + chunk_size]
                content_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=text_chunk),
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                await asyncio.sleep(0.005)  # Small delay for smoother streaming

            # Send final chunk with finish_reason
            final_chunk = ChatCompletionChunk(
                id=request_id,
                created=created,
                model=request.model,
                choices=[ChatCompletionChunkChoice(
                    index=0,
                    delta=DeltaContent(),
                    finish_reason="stop"
                )]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            return

        except Exception as e:
            log_a2a_event("reasoning.fallback", "error", str(e))
            traceback.print_exc()
            sys.stdout.flush()

            # If we already started streaming, we must properly terminate
            if ensemble_started:
                error_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=f"\n\n❌ Error: {str(e)}"),
                        finish_reason=None
                    )]
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                final_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(),
                        finish_reason="stop"
                    )]
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return
            # Fall through to local agent only if not started

    # FALLBACK 2: Use local agent
    if _local_agent:
        local_started = False
        try:
            log_a2a_event("reasoning.local", "started", "Using LocalRAGAgent")

            # Send initial role chunk only if RAG sources weren't displayed
            if not initial_sent:
                initial_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(role="assistant"),
                        finish_reason=None
                    )]
                )
                yield f"data: {initial_chunk.model_dump_json()}\n\n"
            else:
                # Add separator
                separator = "\n\n🤖 **Agent Response**\n\n"
                sep_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=separator),
                        finish_reason=None
                    )]
                )
                yield f"data: {sep_chunk.model_dump_json()}\n\n"

            local_started = True
            start_time = time.time()

            # Process query with local agent
            response = _local_agent.process_query(augmented_query)

            # Handle different response types
            if isinstance(response, dict):
                response_text = response.get("answer", str(response))
            else:
                response_text = str(response)

            # Clean ANSI codes
            response_text = strip_ansi_codes(response_text)

            duration_ms = (time.time() - start_time) * 1000
            log_a2a_event(
                "reasoning.local",
                "success",
                f"Local agent complete",
                duration_ms=f"{duration_ms:.0f}",
                response_length=len(response_text)
            )

            # Log to Oracle DB
            if _event_logger:
                try:
                    # Log API event
                    _event_logger.log_api_event(
                        endpoint="/v1/chat/completions",
                        method="POST",
                        request_data={
                            "model": request.model,
                            "strategy": strategy,
                            "stream": True,
                            "query_preview": user_query[:100]
                        },
                        response_data={
                            "request_id": request_id,
                            "response_length": len(response_text),
                            "status": "success",
                            "backend": "local_agent"
                        },
                        status_code=200,
                        duration_ms=duration_ms
                    )
                    # Log model event
                    _event_logger.log_model_event(
                        model_name=request.model,
                        model_type="local_agent",
                        user_prompt=user_query,
                        response=response_text[:2000],
                        collection_used="unified_rag" if rag_context else None,
                        use_cot=strategy in ["cot", "tot", "react"],
                        duration_ms=duration_ms
                    )
                except Exception as e:
                    print(f"[EventLogger] Error logging to Oracle DB: {e}", flush=True)

            # Stream the response
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                text_chunk = response_text[i:i + chunk_size]
                content_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=text_chunk),
                        finish_reason=None
                    )]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                await asyncio.sleep(0.005)

            # Final chunk
            final_chunk = ChatCompletionChunk(
                id=request_id,
                created=created,
                model=request.model,
                choices=[ChatCompletionChunkChoice(
                    index=0,
                    delta=DeltaContent(),
                    finish_reason="stop"
                )]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            return

        except Exception as e:
            log_a2a_event("reasoning.local", "error", str(e))

            # If we already started streaming, we must properly terminate
            if local_started:
                error_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(content=f"\n\n❌ Error: {str(e)}"),
                        finish_reason=None
                    )]
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                final_chunk = ChatCompletionChunk(
                    id=request_id,
                    created=created,
                    model=request.model,
                    choices=[ChatCompletionChunkChoice(
                        index=0,
                        delta=DeltaContent(),
                        finish_reason="stop"
                    )]
                )
                yield f"data: {final_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return

    # No backend available
    log_a2a_event("chat.completions", "error", "No reasoning backend available")

    # Log error to Oracle DB
    if _event_logger:
        try:
            total_duration_ms = (time.time() - start_time) * 1000
            _event_logger.log_api_event(
                endpoint="/v1/chat/completions",
                method="POST",
                request_data={
                    "model": request.model,
                    "strategy": strategy,
                    "stream": True
                },
                response_data={"error": "No reasoning backend available"},
                status_code=500,
                duration_ms=total_duration_ms
            )
        except Exception as e:
            print(f"[EventLogger] Error logging error to Oracle DB: {e}", flush=True)

    # Send initial role chunk if not already sent
    if not initial_sent:
        initial_chunk = ChatCompletionChunk(
            id=request_id,
            created=created,
            model=request.model,
            choices=[ChatCompletionChunkChoice(
                index=0,
                delta=DeltaContent(role="assistant"),
                finish_reason=None
            )]
        )
        yield f"data: {initial_chunk.model_dump_json()}\n\n"

    error_chunk = ChatCompletionChunk(
        id=request_id,
        created=created,
        model=request.model,
        choices=[ChatCompletionChunkChoice(
            index=0,
            delta=DeltaContent(content="❌ Error: No reasoning backend available"),
            finish_reason=None
        )]
    )
    yield f"data: {error_chunk.model_dump_json()}\n\n"

    final_chunk = ChatCompletionChunk(
        id=request_id,
        created=created,
        model=request.model,
        choices=[ChatCompletionChunkChoice(
            index=0,
            delta=DeltaContent(),
            finish_reason="stop"
        )]
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


async def generate_non_streaming_response(
    request: ChatCompletionRequest,
    model_config: Dict[str, Any],
    rag_context: str = ""
) -> ChatCompletionResponse:
    """
    Generate non-streaming chat completion response.
    """
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    start_time = time.time()

    # Get the user's query
    user_query = ""
    for msg in reversed(request.messages):
        if msg.role.value == "user" and msg.content:
            user_query = msg.content
            break

    if not user_query:
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": "No user message found", "type": "invalid_request_error"}}
        )

    # Build augmented query
    augmented_query = user_query
    if rag_context:
        augmented_query = f"{rag_context}\n\nUser Question: {user_query}"

    strategy = model_config["strategy"]
    response_text = ""
    backend_used = "none"

    # Try reasoning ensemble
    if _reasoning_ensemble:
        try:
            result = await _reasoning_ensemble.run(
                query=augmented_query,
                strategies=[strategy],
                use_rag=False,
                collection="General",
                config=None
            )
            response_text = result.winner.get("response", "No response generated")
            response_text = strip_ansi_codes(response_text)  # Remove ANSI color codes
            backend_used = "reasoning_ensemble"
        except Exception as e:
            print(f"Reasoning ensemble error: {e}", flush=True)

    # Fallback to local agent
    if not response_text and _local_agent:
        try:
            response = _local_agent.process_query(augmented_query)
            if isinstance(response, dict):
                response_text = response.get("answer", str(response))
            else:
                response_text = str(response)
            response_text = strip_ansi_codes(response_text)  # Remove ANSI color codes
            backend_used = "local_agent"
        except Exception as e:
            print(f"Local agent error: {e}", flush=True)

    if not response_text:
        response_text = "Error: No reasoning backend available"

    duration_ms = (time.time() - start_time) * 1000

    # Log to Oracle DB
    if _event_logger:
        try:
            # Log API event
            _event_logger.log_api_event(
                endpoint="/v1/chat/completions",
                method="POST",
                request_data={
                    "model": request.model,
                    "strategy": strategy,
                    "stream": False,
                    "query_preview": user_query[:100]
                },
                response_data={
                    "request_id": request_id,
                    "response_length": len(response_text),
                    "status": "success" if backend_used != "none" else "error",
                    "backend": backend_used
                },
                status_code=200,
                duration_ms=duration_ms
            )
            # Log model event
            if backend_used != "none":
                _event_logger.log_model_event(
                    model_name=request.model,
                    model_type=backend_used,
                    user_prompt=user_query,
                    response=response_text[:2000],
                    collection_used="unified_rag" if rag_context else None,
                    use_cot=strategy in ["cot", "tot", "react"],
                    duration_ms=duration_ms
                )
        except Exception as e:
            print(f"[EventLogger] Error logging to Oracle DB: {e}", flush=True)

    return ChatCompletionResponse(
        id=request_id,
        created=created,
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
        ],
        usage=UsageInfo(
            prompt_tokens=len(augmented_query.split()),
            completion_tokens=len(response_text.split()),
            total_tokens=len(augmented_query.split()) + len(response_text.split())
        )
    )


def extract_text_from_content(content: Union[str, List[ContentPart], None]) -> str:
    """
    Extract text content from a message that may be string or multimodal array.

    OpenAI API supports content as either:
    - A simple string
    - An array of ContentPart objects with type "text", "image_url", etc.

    Returns the concatenated text content.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and part.get("text"):
                    text_parts.append(part["text"])
            elif hasattr(part, "type") and part.type == "text" and part.text:
                text_parts.append(part.text)
        return "\n".join(text_parts)
    return str(content)


def extract_attachments_from_content(content: Union[str, List[ContentPart], None]) -> List[Dict[str, Any]]:
    """
    Extract non-text attachments (images, files, URLs) from multimodal content.

    Returns list of attachment info dicts.
    """
    attachments = []
    if not isinstance(content, list):
        return attachments

    for part in content:
        part_dict = part.model_dump() if hasattr(part, "model_dump") else (part if isinstance(part, dict) else {})
        part_type = part_dict.get("type", "")

        if part_type == "image_url":
            image_info = part_dict.get("image_url", {})
            attachments.append({
                "type": "image",
                "url": image_info.get("url"),
                "detail": image_info.get("detail", "auto")
            })
        elif part_type == "file":
            attachments.append({
                "type": "file",
                "id": part_dict.get("id"),
                "name": part_dict.get("name"),
                "data": part_dict.get("data"),
                "url": part_dict.get("url")
            })
        elif part_type not in ["text", ""]:
            # Capture any other attachment types
            attachments.append({"type": part_type, **part_dict})

    return attachments


def extract_openwebui_sources(message_content: str) -> List[Dict[str, Any]]:
    """
    Extract source content from Open WebUI's preprocessed message format.

    Open WebUI embeds webpage content in messages using <source> tags:
    <source id="1" title="Page Title" url="https://...">
    ...content...
    </source>

    Returns list of source dicts with id, title, url, and content.
    """
    sources = []

    # Pattern to match <source> tags with their attributes and content
    # Open WebUI format: <source id="X" ...attributes...>content</source>
    pattern = re.compile(
        r'<source\s+([^>]*)>(.*?)</source>',
        re.DOTALL | re.IGNORECASE
    )

    for match in pattern.finditer(message_content):
        attrs_str = match.group(1)
        content = match.group(2).strip()

        # Parse attributes
        id_match = re.search(r'id="([^"]*)"', attrs_str)
        title_match = re.search(r'title="([^"]*)"', attrs_str)
        url_match = re.search(r'url="([^"]*)"', attrs_str)
        name_match = re.search(r'name="([^"]*)"', attrs_str)

        source_info = {
            "id": id_match.group(1) if id_match else f"source_{len(sources)}",
            "title": title_match.group(1) if title_match else (name_match.group(1) if name_match else ""),
            "url": url_match.group(1) if url_match else "",
            "content": content
        }

        # Only add if there's actual content
        if content and len(content) > 50:
            sources.append(source_info)

    return sources


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for vector storage.

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation
            for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n', '\n\n']:
                break_point = text.rfind(punct, start + chunk_size // 2, end)
                if break_point != -1:
                    end = break_point + len(punct)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap if end < len(text) else len(text)

    return chunks


async def execute_via_a2a(
    query: str,
    strategy: str,
    use_rag: bool = False,
    collection: str = "General",
    request_id: str = None
) -> Dict[str, Any]:
    """
    Execute a reasoning request via the A2A protocol.

    This routes the request through the A2AHandler which:
    1. Logs the request to Oracle DB event logger
    2. Executes the reasoning strategy
    3. Returns the response in A2A format

    Args:
        query: The user query to process
        strategy: Reasoning strategy (cot, tot, react, etc.)
        use_rag: Whether to use RAG context
        collection: RAG collection to use
        request_id: Optional request ID for tracking

    Returns:
        Dict with response and metadata
    """
    if not _a2a_handler:
        log_a2a_event("a2a.execute", "warning", "A2A handler not available, falling back to direct execution")
        return {"error": "A2A handler not available"}

    try:
        # Import A2A models
        from .a2a_models import A2ARequest

        # Create A2A request for reasoning execution
        a2a_request = A2ARequest(
            method="reasoning.execute",
            params={
                "query": query,
                "strategy": strategy,
                "use_rag": use_rag,
                "collection": collection
            },
            id=request_id or f"openai-{uuid.uuid4().hex[:8]}"
        )

        log_a2a_event(
            "a2a.reasoning",
            "started",
            f"Routing through A2A protocol",
            strategy=strategy,
            request_id=a2a_request.id
        )

        # Execute via A2A handler
        response = await _a2a_handler.handle_request(a2a_request)

        if response.error:
            log_a2a_event("a2a.reasoning", "error", str(response.error))
            return {"error": str(response.error)}

        log_a2a_event(
            "a2a.reasoning",
            "success",
            f"A2A response received",
            request_id=a2a_request.id
        )

        return response.result if response.result else {}

    except Exception as e:
        log_a2a_event("a2a.reasoning", "error", f"A2A execution failed: {e}")
        return {"error": str(e)}


async def persist_openwebui_context_to_rag(message_content: str) -> Dict[str, Any]:
    """
    Extract Open WebUI embedded sources and persist them to Oracle AI Database.

    This function detects when Open WebUI has preprocessed webpage content into
    the message (with <source> tags) and stores the content in the WEBCOLLECTION
    for future RAG retrieval.

    Args:
        message_content: The full message content from Open WebUI

    Returns:
        Dict with status, sources_found, chunks_stored, and any errors
    """
    result = {
        "sources_found": 0,
        "chunks_stored": 0,
        "sources": [],
        "errors": []
    }

    if not _vector_store:
        result["errors"].append("Vector store not initialized")
        return result

    # Check if this looks like Open WebUI preprocessed content
    if "<source" not in message_content:
        return result

    # Extract sources from the message
    sources = extract_openwebui_sources(message_content)
    result["sources_found"] = len(sources)

    if not sources:
        return result

    log_a2a_event(
        "openwebui.context",
        "detected",
        f"Found {len(sources)} embedded sources",
        sources=len(sources)
    )

    for source in sources:
        try:
            source_url = source.get("url", "")
            source_title = source.get("title", "Unknown")
            source_id = source.get("id", "")
            content = source.get("content", "")

            # Generate a unique ID for deduplication
            import hashlib
            content_hash = hashlib.md5(content[:1000].encode()).hexdigest()[:8]
            unique_source_id = f"openwebui_{source_id}_{content_hash}"

            # Chunk the content
            text_chunks = chunk_text(content, chunk_size=800, overlap=100)

            # Prepare chunks for storage
            chunks = []
            for i, chunk_text_item in enumerate(text_chunks):
                chunks.append({
                    "text": chunk_text_item,
                    "metadata": {
                        "source": source_url or f"openwebui_source_{source_id}",
                        "title": source_title,
                        "chunk_id": i,
                        "total_chunks": len(text_chunks),
                        "source_type": "openwebui_attachment",
                        "ingestion_time": datetime.now().isoformat()
                    }
                })

            # Persist to Oracle AI Database
            if chunks:
                _vector_store.add_web_chunks(chunks, unique_source_id)

                log_a2a_event(
                    "openwebui.persist",
                    "success",
                    f"Stored source: {source_title[:50]}",
                    chunks=len(chunks),
                    url=source_url[:60] if source_url else "N/A"
                )

                result["chunks_stored"] += len(chunks)
                result["sources"].append({
                    "id": source_id,
                    "title": source_title,
                    "url": source_url,
                    "chunks": len(chunks)
                })

                # Log to Oracle DB event logger
                if _event_logger:
                    try:
                        _event_logger.log_document_event(
                            document_type="openwebui_webpage",
                            document_id=unique_source_id,
                            source=source_url or f"openwebui_source_{source_id}",
                            chunks_processed=len(chunks),
                            status="success"
                        )
                    except Exception as e:
                        print(f"[EventLogger] Error logging ingest event: {e}", flush=True)

        except Exception as e:
            error_msg = f"Failed to persist source {source.get('id', 'unknown')}: {str(e)}"
            result["errors"].append(error_msg)
            log_a2a_event("openwebui.persist", "error", error_msg)

    return result


async def process_openwebui_url_uploads(request_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process URL uploads from Open WebUI's "Upload Link" functionality.

    When a user uses "Upload Link" in Open WebUI, the URL is passed in the
    request.files array. This function:
    1. Detects URL files in the request
    2. Fetches and processes the URL content using WebProcessor
    3. Persists chunks to WEBCOLLECTION with openwebui_url source
    4. Logs the event to Oracle Autonomous

    Args:
        request_files: List of file attachments from request.files

    Returns:
        Dict with stats: {"urls_processed": int, "chunks_stored": int, "errors": []}
    """
    result = {
        "urls_processed": 0,
        "chunks_stored": 0,
        "errors": [],
        "sources": []
    }

    if not request_files:
        return result

    if not _vector_store:
        result["errors"].append("Vector store not initialized")
        return result

    if not WebProcessor:
        result["errors"].append("WebProcessor not available")
        return result

    processor = WebProcessor(chunk_size=800)

    for file_info in request_files:
        try:
            # Check if this is a URL upload
            file_url = file_info.get("url")
            file_type = file_info.get("type", "")
            file_name = file_info.get("name") or file_info.get("filename", "")

            # Skip non-URL files
            if not file_url:
                continue

            # Validate it's actually a URL
            if not is_url(file_url):
                log_a2a_event(
                    "openwebui.url_upload",
                    "skipped",
                    f"Not a valid URL: {file_url}"
                )
                continue

            log_a2a_event(
                "openwebui.url_upload",
                "processing",
                f"Fetching URL: {file_url}",
                source="Upload Link"
            )

            # Fetch and process the URL
            try:
                chunks = processor.process_url(file_url)
            except Exception as fetch_error:
                error_msg = f"Failed to fetch URL {file_url}: {str(fetch_error)}"
                result["errors"].append(error_msg)
                log_a2a_event("openwebui.url_upload", "error", error_msg)
                continue

            if not chunks:
                log_a2a_event(
                    "openwebui.url_upload",
                    "warning",
                    f"No content extracted from {file_url}"
                )
                continue

            # Add openwebui_url source marker to metadata
            for chunk in chunks:
                chunk["metadata"]["source_type"] = "openwebui_url"
                chunk["metadata"]["upload_method"] = "Upload Link"
                chunk["metadata"]["original_filename"] = file_name

            # Generate unique source ID
            source_id = f"openwebui_url_{uuid.uuid4().hex[:8]}"

            # Persist to WEBCOLLECTION
            _vector_store.add_web_chunks(chunks, source_id)

            result["urls_processed"] += 1
            result["chunks_stored"] += len(chunks)

            # Extract title from first chunk metadata
            title = chunks[0]["metadata"].get("title", file_url) if chunks else file_url
            result["sources"].append({
                "url": file_url,
                "title": title,
                "chunks": len(chunks)
            })

            log_a2a_event(
                "openwebui.url_upload",
                "success",
                f"Stored {len(chunks)} chunks from {file_url}",
                collection="WEBCOLLECTION",
                source_id=source_id
            )

            # Log to Oracle event logger
            if _event_logger:
                try:
                    _event_logger.log_document_event(
                        document_type="openwebui_url",
                        document_id=source_id,
                        source=file_url,
                        chunks_processed=len(chunks),
                        status="success"
                    )
                except Exception as e:
                    print(f"[EventLogger] Error logging URL upload event: {e}", flush=True)

        except Exception as e:
            error_msg = f"Error processing URL upload: {str(e)}"
            result["errors"].append(error_msg)
            log_a2a_event("openwebui.url_upload", "error", error_msg)

    return result


@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Create a chat completion.

    OpenAI-compatible endpoint that processes chat messages using
    our reasoning strategies and optionally RAG context.

    The model parameter determines which reasoning strategy to use:
    - "cot", "cot-rag": Chain of Thought
    - "tot", "tot-rag": Tree of Thoughts
    - "react", "react-rag": ReAct
    - etc.

    Models with "-rag" suffix will perform unified RAG search across
    all collections before reasoning.

    Supports @file and @@file references in messages:
    - @filename.ext → inject file content as temporary context
    - @@filename.ext → add file to RAG storage and inject context

    Also handles Open WebUI attachments:
    - files array in request body
    - Multimodal content arrays with images/files
    - Upload Link URLs (automatically persisted to WEBCOLLECTION)
    """
    # Log parsed request for debugging attachment format
    try:
        # Log if there are files in the request
        if request.files:
            files_data = [f.model_dump() if hasattr(f, 'model_dump') else f for f in request.files]
            print(f"📎 [Attachments] Request contains 'files' field: {json.dumps(files_data, indent=2)}", flush=True)

        # Check for multimodal content in messages
        for i, msg in enumerate(request.messages):
            if isinstance(msg.content, list):
                content_data = [c.model_dump() if hasattr(c, 'model_dump') else c for c in msg.content]
                print(f"📎 [Attachments] Message {i} has multimodal content: {json.dumps(content_data, indent=2)}", flush=True)
            if hasattr(msg, 'images') and msg.images:
                print(f"📎 [Attachments] Message {i} has 'images' field: {msg.images}", flush=True)

        # Log extra request fields
        if request.chat_id:
            print(f"📎 [Attachments] chat_id: {request.chat_id}", flush=True)
        if request.session_id:
            print(f"📎 [Attachments] session_id: {request.session_id}", flush=True)
        if request.metadata:
            print(f"📎 [Attachments] metadata: {json.dumps(request.metadata, indent=2)}", flush=True)

        # Log full message content for first user message (truncated)
        openwebui_persist_result = None
        for msg in request.messages:
            if msg.role.value == "user":
                content_str = extract_text_from_content(msg.content)
                if len(content_str) > 500:
                    # This is likely an Open WebUI preprocessed message with embedded context
                    print(f"📎 [OpenWebUI Context] Detected embedded context in message", flush=True)
                    print(f"📎 [OpenWebUI Context] Full message length: {len(content_str)} chars", flush=True)
                    # Check if it contains source tags (Open WebUI format)
                    if "<source" in content_str:
                        sources = re.findall(r'<source[^>]*id="([^"]*)"[^>]*>', content_str)
                        print(f"📎 [OpenWebUI Context] Found {len(sources)} source references", flush=True)
                        # Persist embedded sources to Oracle AI Database for RAG
                        try:
                            openwebui_persist_result = await persist_openwebui_context_to_rag(content_str)
                            if openwebui_persist_result["chunks_stored"] > 0:
                                print(f"📎 [OpenWebUI Context] ✅ Persisted {openwebui_persist_result['chunks_stored']} chunks to Oracle AI Database", flush=True)
                        except Exception as e:
                            print(f"📎 [OpenWebUI Context] ⚠️ Failed to persist sources: {e}", flush=True)
                    # Check if it contains the user's original query
                    if "User Query:" in content_str or "user query" in content_str.lower():
                        query_match = re.search(r'User Query[:\s]+(.+?)(?:\n|$)', content_str, re.IGNORECASE)
                        if query_match:
                            print(f"📎 [OpenWebUI Context] Original user query: {query_match.group(1)[:100]}", flush=True)
                break

    except Exception as e:
        print(f"⚠️ [Attachments] Failed to log request: {e}", flush=True)
        import traceback
        traceback.print_exc()

    # Validate model
    model_config = get_model_config(request.model)
    if not model_config:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Model '{request.model}' not found. Available models: {list(REASONING_MODELS.keys())}",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }
        )

    # Get user's query for processing (handles both string and multimodal content)
    user_query = ""
    user_message_idx = -1
    message_attachments = []

    for idx, msg in enumerate(reversed(request.messages)):
        if msg.role.value == "user" and msg.content:
            # Extract text from potentially multimodal content
            user_query = extract_text_from_content(msg.content)
            user_message_idx = len(request.messages) - 1 - idx

            # Extract any attachments from multimodal content
            message_attachments = extract_attachments_from_content(msg.content)
            if message_attachments:
                print(f"📎 [Attachments] Extracted from message content: {message_attachments}", flush=True)
            break

    # Also check request-level files (Open WebUI format)
    request_files = []
    if request.files:
        request_files = [f.model_dump() for f in request.files]
        print(f"📎 [Attachments] Request-level files: {json.dumps(request_files, indent=2)}", flush=True)

        # Process URL uploads from "Upload Link" functionality
        # This persists URL content to WEBCOLLECTION for RAG
        try:
            url_upload_result = await process_openwebui_url_uploads(request_files)
            if url_upload_result["urls_processed"] > 0:
                print(f"🔗 [Upload Link] ✅ Processed {url_upload_result['urls_processed']} URLs, stored {url_upload_result['chunks_stored']} chunks to WEBCOLLECTION", flush=True)
                for source in url_upload_result.get("sources", []):
                    print(f"   └─ {source['title'][:50]}... ({source['chunks']} chunks)", flush=True)
            if url_upload_result["errors"]:
                for error in url_upload_result["errors"]:
                    print(f"🔗 [Upload Link] ⚠️ {error}", flush=True)
        except Exception as e:
            print(f"🔗 [Upload Link] ⚠️ Failed to process URL uploads: {e}", flush=True)

    # Process file references (@file and @@file patterns)
    file_context = ""
    file_display_info = []
    cleaned_query = user_query

    if user_query and _file_handler:
        cleaned_query, file_context, file_display_info = await process_file_references(user_query)

        # Update the message with cleaned query (file refs removed)
        if cleaned_query != user_query and user_message_idx >= 0:
            # Create modified messages list
            messages_copy = list(request.messages)
            original_msg = messages_copy[user_message_idx]
            messages_copy[user_message_idx] = ChatMessage(
                role=original_msg.role,
                content=cleaned_query
            )
            request = ChatCompletionRequest(
                model=request.model,
                messages=messages_copy,
                stream=request.stream,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            user_query = cleaned_query

    # Get RAG context if enabled
    rag_context = ""
    rag_results = []
    if model_config["rag"]:
        if user_query:
            rag_results = await unified_rag_search(user_query, top_k=5)
            rag_context = build_rag_context(rag_results)

    # Combine file context with RAG context
    combined_context = ""
    if file_context and rag_context:
        combined_context = f"{file_context}\n\n{rag_context}"
    elif file_context:
        combined_context = file_context
    elif rag_context:
        combined_context = rag_context

    # Generate response
    if request.stream:
        return StreamingResponse(
            generate_streaming_response(
                request,
                model_config,
                combined_context,
                rag_results,
                file_display_info
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        response = await generate_non_streaming_response(request, model_config, combined_context)
        return response


# Health check endpoint
@router.get("/health")
async def openai_health():
    """Health check for OpenAI-compatible API."""
    return {
        "status": "ok",
        "models_available": len(REASONING_MODELS),
        "vector_store_available": _vector_store is not None,
        "reasoning_ensemble_available": _reasoning_ensemble is not None,
        "local_agent_available": _local_agent is not None
    }
