"""A LangGraph agent whose memory lives in Oracle AI Database.

  Thread state   OracleSaver (a LangGraph checkpointer) saves every thread's messages, so a
                 thread continues after the process exits.
  Long-term      OracleStore (a LangGraph store) saves facts about the user, so every thread
  facts          can read them, including threads that started later.

The "model" is a few lines of pattern matching, so no API key is needed. It learns "my X is Y"
and answers "what is my X?". To use a real chat model, replace the body of `reply`; the
persistence code stays the same.

Run these in order, each in its own process:

    ORACLE_PWD=... python agent_memory_langgraph.py --reset "My name is Ada"
    ORACLE_PWD=... python agent_memory_langgraph.py "What is my name?"
    ORACLE_PWD=... python agent_memory_langgraph.py --thread other "What is my name?"

--reset forgets every thread and fact first, so the sequence repeats with the same output.

Environment: ORACLE_PWD (required), ORACLE_DSN (default localhost:1521/FREEPDB1),
ORACLE_USER (default quickstart).
"""

import argparse
import os
import re
import sys

import oracledb
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph_oracledb.checkpoint.oracle import OracleSaver
from langgraph_oracledb.store.oracle import OracleStore

USER_ID = "user-123"
NAMESPACE = ("users", USER_ID)
DEFAULT_THREAD = "demo"


def connect() -> oracledb.Connection:
    password = os.environ.get("ORACLE_PWD")
    if not password:
        sys.exit("Set ORACLE_PWD to the password you passed to docker run.")
    user = os.environ.get("ORACLE_USER", "quickstart")
    dsn = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
    try:
        return oracledb.connect(user=user, password=password, dsn=dsn)
    except oracledb.Error as exc:
        sys.exit(f"Could not connect as {user} to {dsn}: {exc}\nRun setup_database.py first.")


def reply(state: MessagesState, runtime: Runtime) -> dict:
    """The agent's only node. runtime.store is the OracleStore passed to compile()."""
    text = state["messages"][-1].content
    if learned := re.search(r"\bmy ([\w ]+?) is ([\w .'-]+?)\.?$", text, re.IGNORECASE):
        key, value = learned.group(1).lower(), learned.group(2)
        runtime.store.put(NAMESPACE, key, {"value": value})
        answer = f"Noted: your {key} is {value}."
    elif asked := re.search(r"\bwhat is my ([\w ]+?)\??$", text, re.IGNORECASE):
        key = asked.group(1).lower()
        item = runtime.store.get(NAMESPACE, key)
        answer = f"Your {key} is {item.value['value']}." if item else f"I do not know your {key}."
    else:
        answer = "Tell me something like 'My name is Ada', or ask 'What is my name?'."
    return {"messages": [AIMessage(content=answer)]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("message", help="what to say to the agent")
    parser.add_argument("--thread", default=DEFAULT_THREAD, help="conversation id")
    parser.add_argument("--reset", action="store_true", help="forget all threads and facts")
    args = parser.parse_args()

    conn = connect()
    saver = OracleSaver(conn)
    store = OracleStore(conn)
    saver.setup()
    store.setup()
    if args.reset:
        with conn.cursor() as cur:
            cur.execute("select distinct thread_id from checkpoints")
            for (thread_id,) in cur.fetchall():
                saver.delete_thread(thread_id)
        for item in store.search(NAMESPACE, limit=100):
            store.delete(NAMESPACE, item.key)

    builder = StateGraph(MessagesState)
    builder.add_node("reply", reply)
    builder.add_edge(START, "reply")
    builder.add_edge("reply", END)
    graph = builder.compile(checkpointer=saver, store=store)

    config = {"configurable": {"thread_id": args.thread}}
    result = graph.invoke({"messages": [HumanMessage(content=args.message)]}, config)

    print(f"Thread {args.thread!r}, you: {args.message}")
    print(f"Thread {args.thread!r}, agent: {result['messages'][-1].content}")
    print(f"Messages in this thread, read back from the database: {len(result['messages'])}")
    facts = {item.key: item.value["value"] for item in store.search(NAMESPACE, limit=100)}
    print(f"Facts in the long-term store: {facts}")


if __name__ == "__main__":
    main()
