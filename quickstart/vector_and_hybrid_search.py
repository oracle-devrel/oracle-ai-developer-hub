"""Vector search and hybrid search on Oracle AI Database, in plain SQL and through LangChain.

Part 1, SQL (python-oracledb):
  VECTOR column -> vector index -> similarity search with a metadata filter
  -> hybrid vector index -> DBMS_HYBRID_VECTOR.SEARCH (keyword and vector scores in one call)
Part 2, LangChain (langchain-oracledb):
  OracleVS -> create_index -> similarity_search with a filter -> OracleHybridSearchRetriever

Embeddings are computed inside the database by the ONNX model ALL_MINILM_L12_V2 that
setup_database.py loaded. No API key is involved.

Run:  ORACLE_PWD=... python vector_and_hybrid_search.py
Environment: ORACLE_PWD (required), ORACLE_DSN (default localhost:1521/FREEPDB1),
ORACLE_USER (default quickstart).
"""

import json
import os
import sys

import oracledb
from langchain_core.documents import Document
from langchain_oracledb.embeddings import OracleEmbeddings
from langchain_oracledb.retrievers.hybrid_search import (
    OracleHybridSearchRetriever,
    create_hybrid_index,
)
from langchain_oracledb.vectorstores import DistanceStrategy, oraclevs
from langchain_oracledb.vectorstores.oraclevs import OracleVS

MODEL = "ALL_MINILM_L12_V2"

ROWS = [
    (1, "billing", "Premium customers can request a full refund within 30 days."),
    (2, "billing", "Annual plans are billed once a year and prorated on cancellation."),
    (3, "billing", "Invoices are emailed on the first day of each month."),
    (4, "support", "Premium plans include 24/7 support with a one hour response time."),
    (5, "support", "Error ORA-51803 means the vector has a different number of dimensions."),
    (6, "support", "Critical incidents are answered within one hour."),
]
VECTOR_QUERY = "money back"
HYBRID_QUERY = "ORA-51803 vector dimensions"

# Return CLOB columns as str. OracleEmbeddings sets this as a side effect, and the hybrid
# retriever relies on it, so set it here because InDatabaseEmbeddings does not.
oracledb.defaults.fetch_lobs = False


class InDatabaseEmbeddings(OracleEmbeddings):
    """OracleEmbeddings that calls the SQL function VECTOR_EMBEDDING for each text.

    OracleEmbeddings.embed_documents passes Python strings to a collection of CLOBs, which
    python-oracledb in thin mode rejects with DPY-3013 (seen with langchain-oracledb 1.7.0 and
    python-oracledb 26.2.0). The subclass keeps the type, which OracleHybridSearchRetriever
    requires, and replaces only that one method.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self.params["model"]
        with self.conn.cursor() as cur:
            vectors = []
            for text in texts:
                cur.execute(
                    f"select vector_embedding({model} using :text as data) from dual", text=text
                )
                vectors.append(list(cur.fetchone()[0]))
            return vectors


def connect() -> oracledb.Connection:
    password = os.environ.get("ORACLE_PWD")
    if not password:
        sys.exit("Set ORACLE_PWD to the password you passed to docker run.")
    user = os.environ.get("ORACLE_USER", "quickstart")
    dsn = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
    try:
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.Error as exc:
        sys.exit(f"Could not connect as {user} to {dsn}: {exc}\nRun setup_database.py first.")
    with conn.cursor() as cur:
        cur.execute("select count(*) from user_mining_models where model_name = :m", m=MODEL)
        if cur.fetchone()[0] == 0:
            sys.exit(f"Model {MODEL} is not loaded. Run setup_database.py first.")
    return conn


def drop_table(cur: oracledb.Cursor, table: str) -> None:
    cur.execute("select count(*) from user_tables where table_name = :t", t=table.upper())
    if cur.fetchone()[0]:
        cur.execute(f"drop table {table} purge")


def sql_part(conn: oracledb.Connection) -> None:
    with conn.cursor() as cur:
        drop_table(cur, "qs_docs")
        cur.execute(
            """create table qs_docs (
                 id number primary key,
                 category varchar2(30),
                 text varchar2(1000),
                 embedding vector(384, float32))"""
        )
        # The database embeds each sentence itself. The model name is an identifier, not a bind.
        cur.executemany(
            f"""insert into qs_docs (id, category, text, embedding)
                values (:id, :category, :text, vector_embedding({MODEL} using :text as data))""",
            [{"id": i, "category": c, "text": t} for i, c, t in ROWS],
        )
        conn.commit()
        print(f"Loaded {len(ROWS)} rows into QS_DOCS with in-database embeddings.")

        # IVF index. HNSW needs a vector memory pool that a fresh container does not have.
        cur.execute(
            """create vector index qs_docs_ivf on qs_docs (embedding)
               organization neighbor partitions
               distance cosine with target accuracy 95"""
        )

        cur.execute(
            f"""select text, vector_distance(embedding,
                        vector_embedding({MODEL} using :q as data), cosine) as distance
                from qs_docs
                where category = :category
                order by distance
                fetch approximate first 2 rows only""",
            q=VECTOR_QUERY,
            category="billing",
        )
        print(f"SQL vector search for {VECTOR_QUERY!r} (category = billing):")
        for text, distance in cur.fetchall():
            print(f"  distance {distance:.3f}  {text}")

        # The hybrid index keeps a keyword (Oracle Text) index and a vector index on the same
        # column, so one call can score both.
        cur.execute(
            f"create hybrid vector index qs_docs_hybrid on qs_docs (text) parameters('model {MODEL}')"
        )
        search = {
            "hybrid_index_name": "qs_docs_hybrid",
            "search_text": HYBRID_QUERY,
            "return": {"values": ["rowid", "score", "vector_score", "text_score"], "topN": 3},
        }
        cur.execute(
            "select json_serialize(dbms_hybrid_vector.search(json(:search))) from dual",
            search=json.dumps(search),
        )
        hits = json.loads(cur.fetchone()[0])
        print(f"SQL hybrid search for {HYBRID_QUERY!r}:")
        for hit in hits:
            cur.execute("select text from qs_docs where rowid = :r", r=hit["rowid"])
            print(
                f"  score {hit['score']:.1f} (vector {hit['vector_score']:.1f},"
                f" keyword {hit['text_score']:.1f})  {cur.fetchone()[0]}"
            )


def langchain_part(conn: oracledb.Connection) -> None:
    with conn.cursor() as cur:
        drop_table(cur, "qs_lc_docs")
    embeddings = InDatabaseEmbeddings(conn=conn, params={"provider": "database", "model": MODEL})
    docs = [
        Document(page_content=text, metadata={"id": str(i), "category": category})
        for i, category, text in ROWS
    ]
    # OracleVS defaults to Euclidean distance; the model is trained for cosine similarity.
    store = OracleVS.from_documents(
        docs,
        embeddings,
        client=conn,
        table_name="QS_LC_DOCS",
        distance_strategy=DistanceStrategy.COSINE,
    )
    oraclevs.create_index(conn, store, params={"idx_name": "QS_LC_IVF", "idx_type": "IVF"})

    hits = store.similarity_search(VECTOR_QUERY, k=2, filter={"category": "billing"})
    print(f"LangChain vector search for {VECTOR_QUERY!r} (category = billing):")
    for doc in hits:
        print(f"  {doc.page_content}")

    create_hybrid_index(conn, idx_name="QS_LC_HYBRID", vector_store=store)
    retriever = OracleHybridSearchRetriever(
        vector_store=store,
        idx_name="QS_LC_HYBRID",
        search_mode="hybrid",
        k=3,
        return_scores=True,
    )
    print(f"LangChain hybrid search for {HYBRID_QUERY!r}:")
    for doc in retriever.invoke(HYBRID_QUERY):
        print(f"  score {doc.metadata['score']:.1f}  {doc.page_content}")


def main() -> None:
    conn = connect()
    sql_part(conn)
    langchain_part(conn)


if __name__ == "__main__":
    main()
