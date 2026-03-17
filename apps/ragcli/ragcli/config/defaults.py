"""Default configuration values for ragcli."""

DEFAULT_CONFIG = {
    "oracle": {
        "username": "rag_user",
        "password": "",
        "dsn": "localhost:1521/orcl",
        "use_tls": True,
        "tls_wallet_path": None,
        "pool_size": 10,
    },
    "ollama": {
        "endpoint": "http://localhost:11434",
        "embedding_model": "nomic-embed-text",
        "chat_model": "gemma3:270m",
        "timeout": 30,
    },
    "documents": {
        "chunk_size": 1000,
        "chunk_overlap_percentage": 10,
        "supported_formats": ["txt", "md", "pdf"],
        "max_file_size_mb": 100,
        "temp_dir": "./temp",
    },
    "vector_index": {
        "auto_select": True,
        "index_type": "HNSW",
        "dimension": 768,
        "m": 16,
        "ef_construction": 200,
    },
    "rag": {
        "top_k": 5,
        "min_similarity_score": 0.5,
        "use_reranking": False,
    },
    "logging": {
        "level": "INFO",
        "log_file": "./logs/ragcli.log",
        "max_log_size_mb": 50,
        "backup_count": 5,
        "detailed_metrics": True,
    },
    "ui": {
        "theme": "dark",
        "host": "0.0.0.0",
        "port": 7860,
        "share": False,
        "auto_reload": True,
    },
    "app": {
        "app_name": "ragcli",
        "version": "1.0.0",
        "debug": False,
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "cors_origins": ["*"],
        "enable_swagger": True,
    },
    "search": {
        "strategy": "hybrid",
        "rrf_k": 60,
        "weights": {
            "bm25": 1.0,
            "vector": 1.0,
            "graph": 0.8,
        },
        "use_router": True,
    },
    "memory": {
        "session_timeout_min": 30,
        "max_recent_turns": 5,
        "summarize_every": 5,
        "max_summary_tokens": 300,
    },
    "knowledge_graph": {
        "enabled": True,
        "extraction_model": None,
        "max_entities_per_chunk": 10,
        "dedup_threshold": 0.9,
        "max_hops": 2,
    },
    "feedback": {
        "enabled": True,
        "quality_boost_range": 0.15,
        "recalibrate_after": 50,
    },
    "evaluation": {
        "pairs_per_chunk": 2,
        "max_chunks_per_doc": 20,
        "live_scoring": False,
    },
    "sync": {
        "enabled": False,
        "default_poll_interval": 300,
        "debounce_seconds": 2,
        "max_file_size_mb": 50,
        "supported_formats": ["pdf", "md", "txt", "rst"],
    },
}

REQUIRED_FIELDS = {
    "oracle": ["username", "password", "dsn"],
    "ollama": ["endpoint"],
    "documents": ["supported_formats"],
}
