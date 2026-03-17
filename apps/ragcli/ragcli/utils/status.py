"""Status monitoring utilities for ragcli."""

import requests
from typing import Dict, Any
from ragcli.database.oracle_client import OracleClient
from ragcli.config.config_manager import load_config
from rich.console import Console

console = Console()

def check_db_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """Check Oracle DB connection."""
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        result = cursor.fetchone()
        return {"status": "connected", "message": "Oracle DB connected successfully", "active_sessions": "N/A"}
    except Exception as e:
        return {"status": "disconnected", "message": f"Oracle DB connection failed: {str(e)}", "active_sessions": 0}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()

def get_document_stats(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get document and vector stats."""
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM DOCUMENTS")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CHUNKS")
        vector_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_tokens) FROM DOCUMENTS")
        total_tokens = cursor.fetchone()[0] or 0
        
        return {
            "status": "ok" if doc_count > 0 else "empty",
            "documents": doc_count,
            "vectors": vector_count,
            "total_tokens": total_tokens
        }
    except Exception as e:
        return {"status": "error", "documents": 0, "vectors": 0, "total_tokens": 0, "error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()

def check_ollama(config: Dict[str, Any]) -> Dict[str, Any]:
    """Check Ollama API."""
    try:
        endpoint = config['ollama']['endpoint']
        resp = requests.get(f"{endpoint}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = len(resp.json().get('models', []))
            return {"status": "connected", "message": f"Ollama connected ({models} models)"}
        else:
            return {"status": "error", "message": f"Ollama error {resp.status_code}"}
    except Exception as e:
        return {"status": "disconnected", "message": f"Ollama unreachable: {str(e)}"}

def get_overall_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get status of all components."""
    db = check_db_connection(config)
    stats = get_document_stats(config)
    ollama = check_ollama(config)
    
    overall = {
        "database": db,
        "documents": stats,
        "ollama": ollama,
        "healthy": all(s["status"] in ["connected", "ok"] for s in [db, ollama])
    }
    
    return overall

def print_status(status: Dict[str, Any], rich_output: bool = True):
    """Print status in rich format."""
    if rich_output:
        from rich.table import Table
        table = Table(title="ragcli Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        table.add_row("Database", status["database"]["status"], status["database"]["message"])
        table.add_row("Documents", status["documents"]["status"], f"{status['documents']['documents']} docs, {status['documents']['vectors']} vectors")
        table.add_row("Ollama", status["ollama"]["status"], status["ollama"]["message"])
        table.add_row("Overall", "healthy" if status["healthy"] else "issues", "All checks passed" if status["healthy"] else "Some issues detected")
        
        console.print(table)
    else:
        # For logs or JSON
        import json
        print(json.dumps(status, indent=2))


def get_vector_statistics(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed vector database statistics."""
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        # Get basic counts
        cursor.execute("SELECT COUNT(*) FROM DOCUMENTS")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CHUNKS")
        vector_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_tokens) FROM DOCUMENTS")
        total_tokens = cursor.fetchone()[0] or 0
        
        # Get average chunks per document
        avg_chunks = vector_count / doc_count if doc_count > 0 else 0
        
        # Get dimension from config
        dimension = config.get('vector_index', {}).get('dimension', 768)
        index_type = config.get('vector_index', {}).get('index_type', 'HNSW')
        
        return {
            'total_documents': doc_count,
            'total_vectors': vector_count,
            'total_tokens': total_tokens,
            'avg_chunks_per_doc': avg_chunks,
            'dimension': dimension,
            'index_type': index_type,
            'avg_search_latency_ms': 0.0,  # TODO: Track actual search metrics
            'cache_hit_rate': 0.0  # TODO: Implement caching metrics
        }
    except Exception as e:
        return {
            'error': str(e),
            'total_documents': 0,
            'total_vectors': 0,
            'total_tokens': 0,
            'avg_chunks_per_doc': 0,
            'dimension': 768,
            'index_type': 'Unknown'
        }
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()


def get_index_metadata(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get vector index metadata from Oracle."""
    client = OracleClient(config)
    conn = None
    cursor = None
    try:
        conn = client.get_connection()
        cursor = conn.cursor()
        
        # Query index information
        cursor.execute("""
            SELECT index_name, table_name, column_name, status
            FROM user_indexes
            WHERE table_name IN ('CHUNKS', 'DOCUMENTS')
            ORDER BY index_name
        """)
        
        indexes = []
        for row in cursor.fetchall():
            indexes.append({
                'index_name': row[0],
                'table_name': row[1],
                'column_name': row[2] if row[2] else 'N/A',
                'status': row[3]
            })
        
        return {'indexes': indexes}
    except Exception as e:
        return {'error': str(e), 'indexes': []}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        client.close()
