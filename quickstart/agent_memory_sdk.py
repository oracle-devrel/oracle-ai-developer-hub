"""Oracle AI Agent Memory (oracleagentmemory): store a memory, recall it in a later process.

The SDK keeps users, agents, threads and memories in database tables and searches memories by
meaning. Here it embeds with the ONNX model ALL_MINILM_L12_V2 inside the database, and it does
not call a language model, so no API key is needed. Automatic extraction of memories from a
conversation does need a language model, so it is switched off and the script stores the
memory text itself.

Run these in order, each in its own process:

    ORACLE_PWD=... python agent_memory_sdk.py remember --reset "The user prefers answers in French."
    ORACLE_PWD=... python agent_memory_sdk.py remember "Order 4711 was refunded on Monday."
    ORACLE_PWD=... python agent_memory_sdk.py recall "What language does the user want?"

--reset forgets the demo user's earlier memories first, so the sequence repeats with the same
output.

Environment: ORACLE_PWD (required), ORACLE_DSN (default localhost:1521/FREEPDB1),
ORACLE_USER (default quickstart).
"""

import argparse
import os
import sys

import oracledb
from oracleagentmemory.core import MemoryExtractionConfig, SchemaPolicy
from oracleagentmemory.core.embedders import OracleDBEmbedder
from oracleagentmemory.core.oracleagentmemory import OracleAgentMemory

MODEL = "ALL_MINILM_L12_V2"
USER_ID = "user-123"
AGENT_ID = "support-agent"


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    remember = commands.add_parser("remember", help="store a memory")
    remember.add_argument("text")
    remember.add_argument("--reset", action="store_true", help="forget earlier memories first")
    commands.add_parser("recall", help="search the stored memories").add_argument("query")
    args = parser.parse_args()

    conn = connect()
    memory = OracleAgentMemory(
        connection=conn,
        embedder=OracleDBEmbedder(connection=conn, model=MODEL, embedding_dimension=384),
        schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
        memory_store_id="QS_DEMO",
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )

    if args.command == "remember":
        if args.reset:
            memory.delete_user(USER_ID)
        memory.add_memory(args.text, user_id=USER_ID, agent_id=AGENT_ID)
        print(f"Stored memory: {args.text}")
    else:
        results = memory.search(args.query, user_id=USER_ID, agent_id=AGENT_ID, max_results=3)
        print(f"Recalled for {args.query!r}, closest first:")
        for result in results:
            print(f"  distance {result.distance:.3f}  {result.content}")


if __name__ == "__main__":
    main()
