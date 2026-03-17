"""BM25 full-text search via Oracle Text CONTAINS()."""

import re
from typing import List, Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


def escape_oracle_text(query: str) -> str:
    """Escape special Oracle Text characters."""
    special = ['&', '|', '!', '{', '}', '(', ')', '[', ']', '-', '~', '*', '?', '\\']
    escaped = query
    for ch in special:
        escaped = escaped.replace(ch, f'\\{ch}')
    words = escaped.split()
    if len(words) > 1:
        return " OR ".join(words)
    return escaped


class BM25Search:
    def __init__(self, conn):
        self.conn = conn

    def search(
        self,
        query: str,
        top_k: int = 15,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        escaped = escape_oracle_text(query)
        if not escaped.strip():
            return []

        doc_filter = ""
        binds = {"v_query": escaped, "v_top_k": top_k}

        if document_ids:
            doc_binds = {f"d{i}": did for i, did in enumerate(document_ids)}
            placeholders = ",".join(f":d{i}" for i in range(len(document_ids)))
            doc_filter = f"AND c.document_id IN ({placeholders})"
            binds.update(doc_binds)

        sql = f"""
        SELECT c.chunk_id, c.document_id, c.chunk_text, c.chunk_number,
               SCORE(1) AS bm25_score
        FROM CHUNKS c
        WHERE CONTAINS(c.chunk_text, :v_query, 1) > 0
        {doc_filter}
        ORDER BY SCORE(1) DESC
        FETCH FIRST :v_top_k ROWS ONLY
        """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, binds)
                return [
                    {
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "text": str(row[2]) if row[2] else "",
                        "chunk_number": row[3],
                        "bm25_score": float(row[4]),
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.warning(f"BM25 search failed (index may not exist): {e}")
            return []

    @staticmethod
    def create_text_index(conn):
        """Create Oracle Text index on chunks.chunk_text if not exists."""
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT index_name FROM user_indexes WHERE index_name = 'IDX_CHUNKS_TEXT'"
                )
                if cursor.fetchone():
                    return
                cursor.execute("""
                    CREATE INDEX IDX_CHUNKS_TEXT ON CHUNKS(chunk_text)
                    INDEXTYPE IS CTXSYS.CONTEXT
                    PARAMETERS ('SYNC (ON COMMIT)')
                """)
                conn.commit()
                logger.info("Oracle Text index created on CHUNKS.chunk_text")
        except Exception as e:
            logger.warning(f"Failed to create Oracle Text index: {e}")
