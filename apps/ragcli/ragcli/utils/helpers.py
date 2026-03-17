"""General utility helper functions."""

import uuid
import hashlib
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json
from datetime import datetime, timezone


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def hash_file(file_path: str, algorithm: str = 'sha256') -> str:
    """Calculate file hash for deduplication."""
    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def safe_get(data: Dict, keys: List[str], default: Any = None) -> Any:
    """Safely get nested dictionary value."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_env_vars(data: Any, env_dict: Optional[Dict[str, str]] = None) -> Any:
    """Parse environment variables in ${VAR_NAME} format recursively."""
    import os
    import re

    if env_dict is None:
        env_dict = os.environ

    def replace_var(match):
        var_name = match.group(1)
        return env_dict.get(var_name, match.group(0))  # Return original if not found

    if isinstance(data, str):
        return re.sub(r'\$\{([^}]+)\}', replace_var, data)
    elif isinstance(data, dict):
        return {k: parse_env_vars(v, env_dict) for k, v in data.items()}
    elif isinstance(data, list):
        return [parse_env_vars(item, env_dict) for item in data]
    else:
        return data


def to_iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Convert datetime to ISO format string."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


def from_iso_timestamp(iso_str: str) -> datetime:
    """Parse ISO format string to datetime."""
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
    """Flatten a list of lists."""
    return [item for sublist in nested_list for item in sublist]


def find_files_by_extension(directory: str, extensions: List[str]) -> List[Path]:
    """Find all files with specified extensions in directory recursively."""
    path = Path(directory)
    files = []
    for ext in extensions:
        files.extend(path.rglob(f"*.{ext.lstrip('.')}"))
    return files


def calculate_similarity_percentile(scores: List[float], percentile: float = 95) -> float:
    """Calculate percentile from similarity scores."""
    if not scores:
        return 0.0
    scores.sort()
    index = int(len(scores) * percentile / 100)
    return scores[min(index, len(scores) - 1)]


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """Retry function with exponential backoff."""
    import time
    import random

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e

            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            time.sleep(delay)


def load_json_file(file_path: str) -> Dict:
    """Load JSON file safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to load JSON from {file_path}: {e}")


def save_json_file(data: Dict, file_path: str, indent: int = 2):
    """Save data to JSON file."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, default=str)


def ensure_directory(path: Union[str, Path]):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get comprehensive file information."""
    path = Path(file_path)
    stat = path.stat()

    return {
        'path': str(path.absolute()),
        'name': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'size_bytes': stat.st_size,
        'size_human': format_bytes(stat.st_size),
        'modified_time': datetime.fromtimestamp(stat.st_mtime, timezone.utc),
        'created_time': datetime.fromtimestamp(stat.st_ctime, timezone.utc),
        'is_file': path.is_file(),
        'is_dir': path.is_dir(),
        'exists': path.exists()
    }


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID string format."""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def create_progress_bar(total: int, description: str = "Processing"):
    """Create a Rich progress bar (placeholder for actual implementation)."""
    # This would integrate with Rich progress bars
    # For now, just return a simple dict
    return {
        'total': total,
        'current': 0,
        'description': description
    }


def update_progress_bar(progress_bar: Dict, advance: int = 1):
    """Update progress bar (placeholder)."""
    progress_bar['current'] += advance


def get_system_info() -> Dict[str, Any]:
    """Get basic system information."""
    import platform
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture(),
        'machine': platform.machine(),
        'processor': platform.processor()
    }
