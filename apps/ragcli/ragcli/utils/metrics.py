"""Metrics collection and tracking utilities."""

import time
import psutil
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from .logger import get_logger


logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query operation."""
    query_id: str
    query_text: str
    timestamp: float = field(default_factory=time.time)
    embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    total_time_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    retrieved_chunks: int = 0
    similarity_scores: List[float] = field(default_factory=list)
    avg_similarity: float = 0.0
    min_similarity: float = 0.0
    max_similarity: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    status: str = "success"  # success, failed, partial


@dataclass
class UploadMetrics:
    """Metrics for a document upload operation."""
    document_id: str
    filename: str
    file_size_bytes: int
    timestamp: float = field(default_factory=time.time)
    preprocessing_time_ms: float = 0.0
    chunking_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    database_time_ms: float = 0.0
    total_time_ms: float = 0.0
    extracted_text_size_bytes: int = 0
    chunks_created: int = 0
    total_tokens: int = 0
    embedding_size_bytes: int = 0
    ocr_processed: bool = False
    status: str = "success"


@dataclass
class SystemMetrics:
    """System-level metrics."""
    timestamp: float = field(default_factory=time.time)
    total_queries: int = 0
    total_uploads: int = 0
    active_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    uptime_seconds: float = 0.0


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.query_metrics: deque[QueryMetrics] = deque(maxlen=max_history)
        self.upload_metrics: deque[UploadMetrics] = deque(maxlen=max_history)
        self.system_metrics: deque[SystemMetrics] = deque(maxlen=100)  # Keep less system metrics

    def record_query(self, metrics: QueryMetrics):
        """Record query metrics."""
        self.query_metrics.append(metrics)
        logger.info(
            f"Query metrics recorded: {metrics.query_id} - "
            f"total_time={metrics.total_time_ms:.2f}ms, "
            f"tokens={metrics.total_tokens}, "
            f"chunks={metrics.retrieved_chunks}"
        )

    def record_upload(self, metrics: UploadMetrics):
        """Record upload metrics."""
        self.upload_metrics.append(metrics)
        logger.info(
            f"Upload metrics recorded: {metrics.document_id} - "
            f"total_time={metrics.total_time_ms:.2f}ms, "
            f"chunks={metrics.chunks_created}, "
            f"tokens={metrics.total_tokens}"
        )

    def record_system_metrics(self):
        """Record current system metrics."""
        metrics = SystemMetrics()
        metrics.total_queries = len(self.query_metrics)
        metrics.total_uploads = len(self.upload_metrics)
        metrics.memory_usage_mb = psutil.virtual_memory().used / 1024 / 1024
        metrics.cpu_usage_percent = psutil.cpu_percent(interval=1)
        metrics.disk_usage_percent = psutil.disk_usage('/').percent
        metrics.uptime_seconds = time.time() - psutil.boot_time()

        self.system_metrics.append(metrics)

    def get_query_stats(self, last_n: Optional[int] = None) -> Dict[str, Any]:
        """Get query statistics."""
        metrics = list(self.query_metrics)[-last_n:] if last_n else self.query_metrics

        if not metrics:
            return {}

        total_time = sum(m.total_time_ms for m in metrics)
        total_tokens = sum(m.total_tokens for m in metrics)

        return {
            'total_queries': len(metrics),
            'avg_query_time_ms': total_time / len(metrics),
            'avg_tokens_per_query': total_tokens / len(metrics),
            'avg_chunks_retrieved': sum(m.retrieved_chunks for m in metrics) / len(metrics),
            'success_rate': sum(1 for m in metrics if m.status == 'success') / len(metrics),
            'avg_similarity': sum(m.avg_similarity for m in metrics) / len(metrics)
        }

    def get_upload_stats(self, last_n: Optional[int] = None) -> Dict[str, Any]:
        """Get upload statistics."""
        metrics = list(self.upload_metrics)[-last_n:] if last_n else self.upload_metrics

        if not metrics:
            return {}

        total_time = sum(m.total_time_ms for m in metrics)
        total_size = sum(m.file_size_bytes for m in metrics)

        return {
            'total_uploads': len(metrics),
            'avg_upload_time_ms': total_time / len(metrics),
            'avg_file_size_mb': (total_size / len(metrics)) / 1024 / 1024,
            'avg_chunks_per_doc': sum(m.chunks_created for m in metrics) / len(metrics),
            'avg_tokens_per_doc': sum(m.total_tokens for m in metrics) / len(metrics),
            'ocr_usage_rate': sum(1 for m in metrics if m.ocr_processed) / len(metrics)
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        return {
            'queries': self.get_query_stats(),
            'uploads': self.get_upload_stats(),
            'system': self.get_system_stats()
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        if not self.system_metrics:
            return {}

        latest = self.system_metrics[-1]
        return {
            'memory_usage_mb': latest.memory_usage_mb,
            'cpu_usage_percent': latest.cpu_usage_percent,
            'disk_usage_percent': latest.disk_usage_percent,
            'uptime_hours': latest.uptime_seconds / 3600,
            'total_operations': latest.total_queries + latest.total_uploads
        }

    def export_metrics(self, format: str = 'dict') -> Any:
        """Export metrics in specified format."""
        if format == 'dict':
            return {
                'query_metrics': [vars(m) for m in self.query_metrics],
                'upload_metrics': [vars(m) for m in self.upload_metrics],
                'system_metrics': [vars(m) for m in self.system_metrics],
                'summary': self.get_performance_summary()
            }
        elif format == 'json':
            import json
            return json.dumps(self.export_metrics('dict'), default=str, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    return _metrics_collector


def record_query_metrics(query_id: str, **kwargs) -> QueryMetrics:
    """Record query metrics with timing."""
    metrics = QueryMetrics(query_id=query_id, **kwargs)

    if metrics.similarity_scores:
        metrics.avg_similarity = sum(metrics.similarity_scores) / len(metrics.similarity_scores)
        metrics.min_similarity = min(metrics.similarity_scores)
        metrics.max_similarity = max(metrics.similarity_scores)

    # Add system metrics
    metrics.memory_usage_mb = psutil.virtual_memory().used / 1024 / 1024
    metrics.cpu_usage_percent = psutil.cpu_percent()

    _metrics_collector.record_query(metrics)
    return metrics


def record_upload_metrics(document_id: str, **kwargs) -> UploadMetrics:
    """Record upload metrics with timing."""
    metrics = UploadMetrics(document_id=document_id, **kwargs)
    _metrics_collector.record_upload(metrics)
    return metrics


def update_system_metrics():
    """Update system metrics."""
    _metrics_collector.record_system_metrics()


# Performance timing utilities
class Timer:
    """Context manager for timing operations."""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        logger.debug(f"Timing: {self.operation} took {duration_ms:.2f}ms")


def time_function(operation: str):
    """Decorator to time function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timer(operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator
