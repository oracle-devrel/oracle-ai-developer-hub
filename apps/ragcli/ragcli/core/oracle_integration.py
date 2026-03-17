"""
Oracle AI Vector Search Integration for ragcli.
Wraps langchain-oracledb functionality for easier use within the application.
"""

import os
from typing import List, Dict, Any, Optional
import oracledb
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)

# Try importing langchain-oracledb components
try:
    from langchain_oracledb.document_loaders.oracleai import OracleDocLoader, OracleTextSplitter
    from langchain_oracledb.utilities.oracleai import OracleSummary
    from langchain_oracledb.embeddings.oracleai import OracleEmbeddings
    from langchain_oracledb.document_loaders import OracleAutonomousDatabaseLoader
    HAS_ORACLE_LANGCHAIN = True
except ImportError:
    logger.warning("langchain-oracledb not installed. Oracle AI features will be unavailable.")
    HAS_ORACLE_LANGCHAIN = False
    OracleDocLoader = None
    OracleTextSplitter = None
    OracleSummary = None
    OracleEmbeddings = None
    OracleAutonomousDatabaseLoader = None


class OracleIntegrationManager:
    """Manager for Oracle AI Vector Search integrations."""
    
    def __init__(self, conn: oracledb.Connection):
        if not HAS_ORACLE_LANGCHAIN:
            raise ImportError("langchain-oracledb is required for this feature.")
        self.conn = conn

    def load_document(self, file_path: str) -> List[Any]:
        """Load a document using OracleDocLoader."""
        # Note: OracleDocLoader typically loads from DB, but spec says "loading a local file" is possible via params
        # based on README: loader_params["file"] = "<file>"
        params = {"file": file_path}
        loader = OracleDocLoader(conn=self.conn, params=params)
        return loader.load()

    def split_text(self, text: str = None, docs: List[Any] = None, params: Dict = None) -> List[str]:
        """Split text using OracleTextSplitter."""
        # Default params if none provided
        if params is None:
            params = {"normalize": "all"}
            
        splitter = OracleTextSplitter(conn=self.conn, params=params)
        
        chunks = []
        if docs:
            for doc in docs:
                chunks.extend(splitter.split_text(doc.page_content))
        elif text:
            chunks.extend(splitter.split_text(text))
            
        return chunks

    def generate_summary(self, text: str, provider: str = "database", params: Dict = None) -> str:
        """Generate summary using OracleSummary."""
        if params is None:
            params = {
                "provider": provider,
                "glevel": "S",
                "numParagraphs": 1,
                "language": "english"
            }
        
        # Adjust params based on provider if needed, or assume caller passes correct params
        if provider != "database" and "provider" not in params:
            params["provider"] = provider

        summary_tool = OracleSummary(conn=self.conn, params=params)
        return summary_tool.get_summary(text)

    def generate_embeddings(self, texts: List[str], provider: str = "database", params: Dict = None, proxy: str = None) -> List[List[float]]:
        """Generate embeddings using OracleEmbeddings."""
        if params is None:
            params = {"provider": "database", "model": "ALL_MINILM_L12_V2"} # Confirmed existing model
            
        embedder = OracleEmbeddings(conn=self.conn, params=params, proxy=proxy)
        return embedder.embed_documents(texts)
    
    def load_from_adb(self, query: str, **kwargs) -> List[Any]:
        """Load documents from Autonomous Database."""
        # This wrapper might need specific connection info passed if not using current conn
        # typically OracleAutonomousDatabaseLoader takes user/pass/dsn/wallet
        # We'll assume kwargs has specific connection details or we reuse current config if applicable
        # This is a bit complex as it creates its own connection usually.
        loader = OracleAutonomousDatabaseLoader(query=query, **kwargs)
        return loader.load()
