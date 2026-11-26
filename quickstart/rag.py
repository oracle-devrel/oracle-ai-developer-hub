"""Retrieval-augmented generation (RAG) on Oracle AI Database with no API key.

Every retrieval step runs inside the database:
  chunking    OracleTextSplitter splits the documents into sentence-sized chunks
              (DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS)
  embeddings  the ONNX model ALL_MINILM_L12_V2 turns each chunk into a 384-dimension vector
  storage     OracleVS keeps chunks and vectors in a table and runs the similarity search
  chain       a LangChain (LCEL) chain builds a prompt from the best chunks

The script prints the retrieved chunks and the prompt that would go to a language model.
To also generate an answer, run a local Ollama model and name it:

    pip install langchain-ollama
    ollama pull llama3.2:1b
    OLLAMA_MODEL=llama3.2:1b ORACLE_PWD=... python rag.py

Run:  ORACLE_PWD=... python rag.py
Environment: ORACLE_PWD (required), ORACLE_DSN (default localhost:1521/FREEPDB1),
ORACLE_USER (default quickstart), OLLAMA_MODEL (optional), OLLAMA_BASE_URL (optional,
default http://localhost:11434).
"""

import os
import sys

import oracledb
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_oracledb.document_loaders.oracleai import OracleTextSplitter
from langchain_oracledb.embeddings import OracleEmbeddings
from langchain_oracledb.vectorstores import DistanceStrategy
from langchain_oracledb.vectorstores.oraclevs import OracleVS

MODEL = "ALL_MINILM_L12_V2"
TABLE = "QS_RAG_CHUNKS"

SOURCES = {
    "refund-policy": (
        "Premium customers can request a full refund within 30 days of purchase. "
        "Refunds for annual plans are prorated after the first 30 days. "
        "Refunds are issued to the original payment method within 5 business days."
    ),
    "support-policy": (
        "Support is available 24/7 for premium plans. "
        "Standard plans get support on business days from 9am to 5pm. "
        "Critical incidents are answered within one hour."
    ),
}
QUESTION = "How long do premium customers have to ask for a refund?"

PROMPT = ChatPromptTemplate.from_template(
    "Answer the question using only the context below. Keep the answer short.\n\n"
    "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
)


class InDatabaseEmbeddings(OracleEmbeddings):
    """OracleEmbeddings that calls the SQL function VECTOR_EMBEDDING for each text.

    OracleEmbeddings.embed_documents passes Python strings to a collection of CLOBs, which
    python-oracledb in thin mode rejects with DPY-3013 (seen with langchain-oracledb 1.7.0 and
    python-oracledb 26.2.0). The subclass keeps the type and replaces only that one method.
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


def chunk_documents(conn: oracledb.Connection) -> list[Document]:
    splitter = OracleTextSplitter(
        conn=conn, params={"by": "words", "max": 20, "split": "sentence", "normalize": "all"}
    )
    return [
        Document(page_content=chunk, metadata={"source": source})
        for source, text in SOURCES.items()
        for chunk in splitter.split_text(text)
    ]


def make_llm():
    """Return a local Ollama chat model if OLLAMA_MODEL is set, otherwise None."""
    name = os.environ.get("OLLAMA_MODEL")
    if not name:
        return None
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        sys.exit("OLLAMA_MODEL is set, so install the client first: pip install langchain-ollama")
    return ChatOllama(
        model=name,
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )


def main() -> None:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("select count(*) from user_tables where table_name = :t", t=TABLE)
        if cur.fetchone()[0]:
            cur.execute(f"drop table {TABLE} purge")

    chunks = chunk_documents(conn)
    print(f"Split {len(SOURCES)} documents into {len(chunks)} chunks inside the database.")

    embeddings = InDatabaseEmbeddings(conn=conn, params={"provider": "database", "model": MODEL})
    store = OracleVS.from_documents(
        chunks,
        embeddings,
        client=conn,
        table_name=TABLE,
        distance_strategy=DistanceStrategy.COSINE,
    )

    print(f"Question: {QUESTION}")
    retriever = store.as_retriever(search_kwargs={"k": 2})
    docs = retriever.invoke(QUESTION)
    print("Retrieved context:")
    for doc in docs:
        print(f"  [{doc.metadata['source']}] {doc.page_content}")

    inputs = {
        "context": "\n".join(f"- {doc.page_content}" for doc in docs),
        "question": QUESTION,
    }
    llm = make_llm()
    if llm is None:
        print("Prompt that would go to a language model:")
        print(PROMPT.invoke(inputs).to_string())
        print("No model set. To generate an answer, set OLLAMA_MODEL (see the file header).")
        return

    chain = PROMPT | llm | StrOutputParser()
    print(f"Answer from {llm.model}: {chain.invoke(inputs)}")


if __name__ == "__main__":
    main()
