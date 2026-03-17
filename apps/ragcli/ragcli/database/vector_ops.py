"""Vector operations for Oracle DB 26ai in ragcli."""

import json
from typing import List, Tuple, Dict, Any, Optional
import oracledb
from ..utils.logger import get_logger
from ..utils.helpers import generate_uuid as generate_id

logger = get_logger(__name__)


def _build_doc_id_binds(document_ids: List[str]) -> Tuple[Dict[str, str], str]:
    """Return (bind_dict, placeholder_string) for an Oracle IN clause over document_ids."""
    binds = {f"d{i}": did for i, did in enumerate(document_ids)}
    placeholders = ",".join(f":d{i}" for i in range(len(document_ids)))
    return binds, placeholders

def insert_document(
    conn: oracledb.Connection,
    filename: str,
    file_format: str,
    file_size_bytes: int,
    extracted_text_size_bytes: Optional[int],
    chunk_count: int,
    total_tokens: int,
    embedding_dimension: int = 768,
    ocr_processed: str = 'N',
    metadata: Dict = None
) -> str:
    """Insert a new document and return its ID."""
    doc_id = generate_id()
    metadata_json = json.dumps(metadata or {})
    
    approx_emb_size = chunk_count * embedding_dimension * 4  # bytes, float32
    
    sql = """
    INSERT INTO DOCUMENTS (
        document_id, filename, file_format, file_size_bytes, extracted_text_size_bytes,
        chunk_count, total_tokens, embedding_dimension, approximate_embedding_size_bytes,
        ocr_processed, metadata_json
    ) VALUES (
        :v_doc_id, :v_filename, :v_file_format, :v_file_size_bytes, :v_extracted_size,
        :v_chunk_count, :v_total_tokens, :v_dim, :v_approx_size, :v_ocr,
        :v_metadata
    )
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, {
            'v_doc_id': doc_id,
            'v_filename': filename,
            'v_file_format': file_format,
            'v_file_size_bytes': file_size_bytes,
            'v_extracted_size': extracted_text_size_bytes,
            'v_chunk_count': chunk_count,
            'v_total_tokens': total_tokens,
            'v_dim': embedding_dimension,
            'v_approx_size': approx_emb_size,
            'v_ocr': ocr_processed,
            'v_metadata': metadata_json
        })
    return doc_id

def insert_chunk(
    conn: oracledb.Connection,
    doc_id: str,
    chunk_number: int,
    chunk_text: str,
    token_count: int,
    character_count: int,
    start_pos: int = 0,
    end_pos: int = 0,
    embedding: List[float] = None,
    embedding_model: str = "nomic-embed-text"
) -> str:
    """Insert a chunk with embedding."""
    chunk_id = generate_id()
    
    sql = """
    INSERT INTO CHUNKS (
        chunk_id, document_id, chunk_number, chunk_text, token_count,
        character_count, start_position, end_position, chunk_embedding, embedding_model
    ) VALUES (
        :v_chunk_id, :v_doc_id, :v_chunk_num, :v_text, :v_token_count,
        :v_char_count, :v_start, :v_end, TO_VECTOR(:v_embedding), :v_model
    )
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, {
            'v_chunk_id': chunk_id,
            'v_doc_id': doc_id,
            'v_chunk_num': chunk_number,
            'v_text': chunk_text,
            'v_token_count': token_count,
            'v_char_count': character_count,
            'v_start': start_pos,
            'v_end': end_pos,
            'v_embedding': json.dumps(embedding or []),
            'v_model': embedding_model
        })
    return chunk_id

def search_similar(
    conn: oracledb.Connection,
    query_embedding: List[float],
    top_k: int = 5,
    min_similarity: float = 0.5,
    document_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Search for similar chunks using vector similarity."""
    sql_base = """
    SELECT c.chunk_id, c.document_id, c.chunk_text, c.chunk_number,
           VECTOR_DISTANCE(c.chunk_embedding, TO_VECTOR(:v_query_emb), COSINE) AS similarity_score,
           c.chunk_embedding
    FROM CHUNKS c
    """
    binds = {
        'v_query_emb': json.dumps(query_embedding),
        'v_top_k': top_k
    }
    if document_ids:
        doc_binds, placeholders = _build_doc_id_binds(document_ids)
        sql_base += f" WHERE c.document_id IN ({placeholders}) "
        binds.update(doc_binds)

    sql = sql_base + """
    ORDER BY similarity_score ASC
    FETCH FIRST :v_top_k ROWS ONLY
    """

    with conn.cursor() as cursor:
        cursor.execute(sql, binds)

        results = []
        for row in cursor:
            score = 1 - row[4]  # Convert distance to similarity (cosine similarity = 1 - distance)
            if score >= min_similarity:
                chunk_text_val = str(row[2]) if row[2] else ""
                db_embedding = row[5]
                if hasattr(db_embedding, 'tolist'):
                    embedding_list = db_embedding.tolist()
                else:
                    embedding_list = list(db_embedding) if db_embedding else []

                results.append({
                    'chunk_id': row[0],
                    'document_id': row[1],
                    'chunk_number': row[3],
                    'text': chunk_text_val,
                    'similarity_score': score,
                    'embedding': embedding_list
                })

    return results


def create_vector_index(conn: oracledb.Connection, config: Dict[str, Any]) -> None:
    """Create vector index based on chunk count and configuration."""
    # Check if index already exists
    with conn.cursor() as cursor:
        try:
            cursor.execute("SELECT index_name FROM user_indexes WHERE index_name = 'CHUNKS_EMBEDDING_IDX'")
            if cursor.fetchone():
                logger.info("Vector index already exists, skipping creation")
                return
        except oracledb.Error:
            pass  # Table/index metadata query failed, continue to create

        # Get chunk count to determine index type
        cursor.execute("SELECT COUNT(*) FROM CHUNKS")
        chunk_count = cursor.fetchone()[0]

        # Auto-select index type based on chunk count (from spec)
        if chunk_count <= 1000:
            index_type = "IVF_FLAT"
            index_params = ""
        elif chunk_count <= 100000:
            index_type = "HNSW"
            index_params = "WITH (m=16, ef_construction=200)"
        else:
            index_type = "HYBRID"
            index_params = "WITH (m=16, ef_construction=200)"

        # Get accuracy from config
        accuracy = int(config.get('vector_index', {}).get('accuracy', 95))

        # Create index
        index_sql = f"""
        CREATE VECTOR INDEX CHUNKS_EMBEDDING_IDX
        ON CHUNKS(chunk_embedding)
        ORGANIZATION CLUSTER
        WITH TARGET ACCURACY {accuracy}
        {index_params}
        DISTANCE METRIC COSINE
        """

        try:
            logger.info(f"Creating {index_type} vector index for {chunk_count} chunks")
            cursor.execute(index_sql)
            conn.commit()
            logger.info(f"Vector index created successfully: {index_type}")
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}", exc_info=True)
            conn.rollback()


def log_query(
    conn: oracledb.Connection,
    query_text: str,
    query_embedding: List[float],
    selected_documents: Optional[List[str]],
    top_k: int,
    similarity_threshold: float,
    results: List[Dict[str, Any]],
    response_text: str,
    response_tokens: int,
    timing: Dict[str, float]
) -> str:
    """Log query and results to database."""
    query_id = generate_id()

    # Insert query
    sql = """
    INSERT INTO QUERIES (
        query_id, query_text, query_embedding, selected_documents, top_k,
        similarity_threshold, response_text, response_tokens,
        embedding_time_ms, search_time_ms, generation_time_ms
    ) VALUES (
        :v_query_id, :v_query_text, TO_VECTOR(:v_query_emb), :v_docs, :v_top_k,
        :v_threshold, :v_response, :v_resp_tokens,
        :v_emb_time, :v_search_time, :v_gen_time
    )
    """

    docs_str = ",".join(selected_documents) if selected_documents else None

    with conn.cursor() as cursor:
        cursor.execute(sql, {
            'v_query_id': query_id,
            'v_query_text': query_text,
            'v_query_emb': json.dumps(query_embedding),
            'v_docs': docs_str,
            'v_top_k': top_k,
            'v_threshold': similarity_threshold,
            'v_response': response_text,
            'v_resp_tokens': response_tokens,
            'v_emb_time': timing.get('embedding_time_ms', 0),
            'v_search_time': timing.get('search_time_ms', 0),
            'v_gen_time': timing.get('generation_time_ms', 0)
        })

        # Insert query results
        result_sql = """
        INSERT INTO QUERY_RESULTS (
            result_id, query_id, chunk_id, similarity_score, rank
        ) VALUES (
            :result_id, :query_id, :chunk_id, :score, :rank
        )
        """
        for rank, result in enumerate(results[:top_k], start=1):
            cursor.execute(result_sql, {
                'result_id': generate_id(),
                'query_id': query_id,
                'chunk_id': result['chunk_id'],
                'score': result['similarity_score'],
                'rank': rank,
            })

    conn.commit()
    return query_id


def get_embedding_graph(
    conn: oracledb.Connection,
    min_similarity: float = 0.5,
    top_k: int = 10,
    document_ids: Optional[List[str]] = None,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Build a graph of chunk embeddings connected by cosine similarity.
    Uses Oracle VECTOR_DISTANCE for server-side similarity computation.
    """
    with conn.cursor() as cursor:
        # Step 1: Get nodes (chunks with metadata)
        node_sql = """
        SELECT c.chunk_id, c.document_id, d.filename, c.chunk_number,
               DBMS_LOB.SUBSTR(c.chunk_text, 100, 1) AS text_preview,
               c.token_count
        FROM CHUNKS c
        JOIN DOCUMENTS d ON c.document_id = d.document_id
        """
        node_binds = {}
        if document_ids:
            doc_binds, placeholders = _build_doc_id_binds(document_ids)
            node_sql += f" WHERE c.document_id IN ({placeholders})"
            node_binds.update(doc_binds)
        node_sql += f" FETCH FIRST {int(limit)} ROWS ONLY"

        cursor.execute(node_sql, node_binds)
        nodes = []
        node_ids = set()
        for row in cursor:
            text_preview = str(row[4]) if row[4] else ""
            nodes.append({
                "id": row[0],
                "document_id": row[1],
                "document_name": row[2],
                "chunk_number": row[3],
                "text_preview": text_preview,
                "token_count": row[5] or 0,
                "node_type": "chunk"
            })
            node_ids.add(row[0])

        if len(nodes) < 2:
            return {"nodes": nodes, "edges": [], "total_chunks": len(nodes)}

        # Step 2: Compute pairwise similarities using VECTOR_DISTANCE
        min_distance = 1.0 - min_similarity

        doc_filter = ""
        edge_binds = {
            "min_distance": min_distance,
            "top_k": top_k
        }
        if document_ids:
            doc_binds, placeholders = _build_doc_id_binds(document_ids)
            doc_filter = f" WHERE c.document_id IN ({placeholders})"
            edge_binds.update(doc_binds)

        edge_sql = f"""
        WITH target_chunks AS (
            SELECT c.chunk_id
            FROM CHUNKS c
            JOIN DOCUMENTS d ON c.document_id = d.document_id
            {doc_filter}
            FETCH FIRST {int(limit)} ROWS ONLY
        )
        SELECT source_id, target_id, similarity FROM (
            SELECT a.chunk_id AS source_id,
                   b.chunk_id AS target_id,
                   (1 - VECTOR_DISTANCE(a.chunk_embedding, b.chunk_embedding, COSINE)) AS similarity,
                   ROW_NUMBER() OVER (PARTITION BY a.chunk_id ORDER BY VECTOR_DISTANCE(a.chunk_embedding, b.chunk_embedding, COSINE) ASC) AS rn
            FROM CHUNKS a
            CROSS JOIN CHUNKS b
            WHERE a.chunk_id < b.chunk_id
              AND a.chunk_id IN (SELECT chunk_id FROM target_chunks)
              AND b.chunk_id IN (SELECT chunk_id FROM target_chunks)
              AND VECTOR_DISTANCE(a.chunk_embedding, b.chunk_embedding, COSINE) <= :min_distance
        ) WHERE rn <= :top_k
        """

        cursor.execute(edge_sql, edge_binds)
        edges = []
        for row in cursor:
            source_id, target_id, similarity = row[0], row[1], row[2]
            if source_id in node_ids and target_id in node_ids:
                edges.append({
                    "source": source_id,
                    "target": target_id,
                    "similarity": float(similarity)
                })

    return {"nodes": nodes, "edges": edges, "total_chunks": len(nodes)}


def get_query_graph(
    conn: oracledb.Connection,
    query_embedding: List[float],
    query_text: str,
    min_similarity: float = 0.5,
    top_k: int = 10,
    document_ids: Optional[List[str]] = None,
    limit: int = 500
) -> Dict[str, Any]:
    """Build a graph that includes a query node connected to similar chunks."""
    result = get_embedding_graph(conn, min_similarity, top_k, document_ids, limit)

    query_node = {
        "id": "query",
        "document_id": "",
        "document_name": "",
        "chunk_number": 0,
        "text_preview": query_text[:100],
        "token_count": 0,
        "node_type": "query"
    }
    result["nodes"].insert(0, query_node)

    with conn.cursor() as cursor:
        sim_sql = """
        SELECT c.chunk_id,
               (1 - VECTOR_DISTANCE(c.chunk_embedding, TO_VECTOR(:v_query_emb), COSINE)) AS similarity
        FROM CHUNKS c
        """
        sim_binds = {"v_query_emb": json.dumps(query_embedding), "v_top_k": top_k}
        if document_ids:
            doc_binds, placeholders = _build_doc_id_binds(document_ids)
            sim_sql += f" WHERE c.document_id IN ({placeholders})"
            sim_binds.update(doc_binds)

        sim_sql += """
        ORDER BY VECTOR_DISTANCE(c.chunk_embedding, TO_VECTOR(:v_query_emb), COSINE) ASC
        FETCH FIRST :v_top_k ROWS ONLY
        """

        cursor.execute(sim_sql, sim_binds)

        node_ids = {n["id"] for n in result["nodes"]}
        for row in cursor:
            chunk_id, similarity = row[0], float(row[1])
            if chunk_id in node_ids and similarity >= min_similarity:
                result["edges"].append({
                    "source": "query",
                    "target": chunk_id,
                    "similarity": similarity
                })

    return result


# TODO: Batch inserts, retries, index maintenance
