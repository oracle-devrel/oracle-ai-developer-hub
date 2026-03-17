"""Rich-integrated logging configuration."""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import rich.logging
from rich.console import Console
from ..config.config_manager import load_config


def setup_logging(config: Optional[dict] = None, name: str = "ragcli") -> logging.Logger:
    """Set up logging with Rich console output and file rotation.

    Args:
        config: Configuration dictionary with logging settings
        name: Logger name

    Returns:
        Configured logger instance
    """
    if config is None:
        config = load_config()

    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    log_file = log_config.get('log_file', './logs/ragcli.log')
    max_size = log_config.get('max_log_size_mb', 50) * 1024 * 1024
    backup_count = log_config.get('backup_count', 5)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Console handler with Rich
    console = Console()
    rich_handler = rich.logging.RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=False,  # Avoid clutter
        rich_tracebacks=True,
        tracebacks_show_locals=False
    )
    rich_handler.setLevel(level)
    logger.addHandler(rich_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)

    # File formatter (more detailed)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "ragcli") -> logging.Logger:
    """Get or create logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # If no handlers, set up logging
        setup_logging(name=name)
    return logger


class LoggerMixin:
    """Mixin class to add logging to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_performance(logger: logging.Logger, operation: str, duration_ms: float, **kwargs):
    """Log performance metrics.

    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        **kwargs: Additional context
    """
    extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"PERF: {operation} completed in {duration_ms:.2f}ms {extra_info}")


def log_error_with_context(logger: logging.Logger, error: Exception, operation: str, **kwargs):
    """Log error with context information.

    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation being performed
        **kwargs: Additional context
    """
    extra_info = " ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(f"ERROR in {operation}: {str(error)} {extra_info}", exc_info=True)


def log_query_metrics(logger: logging.Logger, query_id: str, **metrics):
    """Log query-specific metrics.

    Args:
        logger: Logger instance
        query_id: Query identifier
        **metrics: Metric key-value pairs
    """
    metrics_str = " ".join(f"{k}={v}" for k, v in metrics.items())
    logger.info(f"QUERY: {query_id} - {metrics_str}")


def log_upload_metrics(logger: logging.Logger, doc_id: str, **metrics):
    """Log document upload metrics.

    Args:
        logger: Logger instance
        doc_id: Document identifier
        **metrics: Metric key-value pairs
    """
    metrics_str = " ".join(f"{k}={v}" for k, v in metrics.items())
    logger.info(f"UPLOAD: {doc_id} - {metrics_str}")
