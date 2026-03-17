"""Input validation utilities."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(f"{field}: {message}" if field else message)


def validate_file_path(file_path: str, config: Optional[dict] = None) -> Path:
    """Validate file path for document upload.

    Args:
        file_path: Path to validate
        config: Configuration dictionary

    Returns:
        Path object if valid

    Raises:
        ValidationError: If path is invalid
    """
    if config is None:
        from ..config.config_manager import load_config
        config = load_config()

    try:
        path = Path(file_path)
    except Exception as e:
        raise ValidationError(f"Invalid path format: {e}", "file_path")

    if not path.exists():
        raise ValidationError("File does not exist", "file_path")

    if not path.is_file():
        raise ValidationError("Path is not a file", "file_path")

    # Check file format
    supported_formats = config.get('documents', {}).get('supported_formats', ['txt', 'md', 'pdf'])
    file_format = path.suffix.lstrip('.').lower()
    if file_format not in supported_formats:
        raise ValidationError(
            f"Unsupported format '{file_format}'. Supported: {', '.join(supported_formats)}",
            "file_format"
        )

    # Check file size
    max_size_mb = config.get('documents', {}).get('max_file_size_mb', 100)
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = path.stat().st_size

    if file_size > max_size_bytes:
        raise ValidationError(
            f"File too large ({file_size / 1024 / 1024:.1f}MB > {max_size_mb}MB)",
            "file_size"
        )

    if file_size == 0:
        raise ValidationError("File is empty", "file_size")

    return path


def validate_query_text(query: str) -> str:
    """Validate query text.

    Args:
        query: Query string to validate

    Returns:
        Stripped query string

    Raises:
        ValidationError: If query is invalid
    """
    if not isinstance(query, str):
        raise ValidationError("Query must be a string", "query")

    query = query.strip()

    if not query:
        raise ValidationError("Query cannot be empty", "query")

    min_length = 3
    max_length = 5000

    if len(query) < min_length:
        raise ValidationError(f"Query too short (min {min_length} characters)", "query")

    if len(query) > max_length:
        raise ValidationError(f"Query too long (max {max_length} characters)", "query")

    # Check for potentially harmful content (basic)
    dangerous_patterns = [
        r'<script',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'vbscript:',  # VBScript URLs
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValidationError("Query contains potentially harmful content", "query")

    return query


def validate_document_ids(doc_ids: List[str], config: Optional[dict] = None) -> List[str]:
    """Validate document ID list.

    Args:
        doc_ids: List of document IDs
        config: Configuration dictionary (unused for now)

    Returns:
        Validated and deduplicated list

    Raises:
        ValidationError: If IDs are invalid
    """
    if not isinstance(doc_ids, list):
        raise ValidationError("Document IDs must be a list", "document_ids")

    if not doc_ids:
        return []  # Empty list is valid

    # Validate each ID format (assuming UUID format)
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)

    validated_ids = []
    for doc_id in doc_ids:
        if not isinstance(doc_id, str):
            raise ValidationError(f"Document ID must be string, got {type(doc_id)}", "document_ids")

        doc_id = doc_id.strip()
        if not doc_id:
            continue  # Skip empty strings

        if not uuid_pattern.match(doc_id):
            raise ValidationError(f"Invalid document ID format: {doc_id}", "document_ids")

        if doc_id not in validated_ids:  # Deduplicate
            validated_ids.append(doc_id)

    max_docs = 50  # Reasonable limit
    if len(validated_ids) > max_docs:
        raise ValidationError(f"Too many documents (max {max_docs})", "document_ids")

    return validated_ids


def validate_top_k(top_k: int, config: Optional[dict] = None) -> int:
    """Validate top-k parameter.

    Args:
        top_k: Number of results to retrieve
        config: Configuration dictionary

    Returns:
        Validated top_k

    Raises:
        ValidationError: If invalid
    """
    if config is None:
        from ..config.config_manager import load_config
        config = load_config()

    default_top_k = config.get('rag', {}).get('top_k', 5)
    min_top_k = 1
    max_top_k = 100

    if top_k is None:
        return default_top_k

    if not isinstance(top_k, int):
        raise ValidationError("top_k must be an integer", "top_k")

    if top_k < min_top_k:
        raise ValidationError(f"top_k too small (min {min_top_k})", "top_k")

    if top_k > max_top_k:
        raise ValidationError(f"top_k too large (max {max_top_k})", "top_k")

    return top_k


def validate_similarity_threshold(threshold: float, config: Optional[dict] = None) -> float:
    """Validate similarity threshold.

    Args:
        threshold: Similarity threshold (0.0 to 1.0)
        config: Configuration dictionary

    Returns:
        Validated threshold

    Raises:
        ValidationError: If invalid
    """
    if config is None:
        from ..config.config_manager import load_config
        config = load_config()

    default_threshold = config.get('rag', {}).get('min_similarity_score', 0.5)
    min_threshold = 0.0
    max_threshold = 1.0

    if threshold is None:
        return default_threshold

    if not isinstance(threshold, (int, float)):
        raise ValidationError("Similarity threshold must be a number", "similarity_threshold")

    if threshold < min_threshold or threshold > max_threshold:
        raise ValidationError(
            f"Similarity threshold must be between {min_threshold} and {max_threshold}",
            "similarity_threshold"
        )

    return float(threshold)


def validate_config(config: dict) -> dict:
    """Validate configuration dictionary.

    Args:
        config: Configuration to validate

    Returns:
        Validated config

    Raises:
        ValidationError: If config is invalid
    """
    required_sections = ['oracle', 'ollama', 'documents', 'vector_index', 'rag', 'logging', 'ui']

    for section in required_sections:
        if section not in config:
            raise ValidationError(f"Missing required config section: {section}", "config")

    # Validate Oracle config
    oracle = config['oracle']
    required_oracle = ['username', 'password', 'dsn']
    for key in required_oracle:
        if key not in oracle:
            raise ValidationError(f"Missing Oracle config: {key}", "oracle")

    # Validate Ollama config
    ollama = config['ollama']
    required_ollama = ['endpoint', 'embedding_model', 'chat_model']
    for key in required_ollama:
        if key not in ollama:
            raise ValidationError(f"Missing Ollama config: {key}", "ollama")

    # Validate vector index
    vector = config['vector_index']
    if 'dimension' not in vector:
        raise ValidationError("Missing vector dimension", "vector_index")

    return config


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace dangerous characters
    dangerous_chars = '<>:"/\\|?*'
    sanitized = filename

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')

    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        name = name[:max_length - len(ext) - 1] if ext else name[:max_length]
        sanitized = f"{name}.{ext}" if ext else name

    return sanitized.strip()
