"""Prepare a local Oracle AI Database for the quick start. Safe to run again.

What it does:
  1. Waits until the database accepts connections.
  2. Creates the user QUICKSTART (or resets its password) and grants it what the examples need.
  3. Loads the ONNX embedding model ALL_MINILM_L12_V2 into that user's schema, unless it is
     already there. The model is a public download from Oracle (about 117 MB), cached in the
     system temp directory. It goes into the database as a BLOB, so no server directory, no
     `docker cp` and no DBA access to the file system are needed.

Run it once after the database container reports it is ready:

    ORACLE_PWD=... python setup_database.py

Environment:
  ORACLE_PWD   required. Password of SYSTEM in the container, and of the new user QUICKSTART.
               Use it for local, throwaway databases only.
  ORACLE_DSN   default localhost:1521/FREEPDB1
  ORACLE_USER  default quickstart (the user to create)
"""

import json
import os
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import oracledb

MODEL_NAME = "ALL_MINILM_L12_V2"
MODEL_URL = (
    "https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/"
    "TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6/n/adwc4pm/b/"
    "OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip"
)
MODEL_FILE_IN_ZIP = "all_MiniLM_L12_v2.onnx"
# Tells the database to treat the file as a text embedding model that takes one string.
MODEL_METADATA = {
    "function": "embedding",
    "embeddingOutput": "embedding",
    "input": {"input": ["DATA"]},
}
WAIT_SECONDS = 300
# The smallest set that lets every script here run. Agent Memory creates tables with identity
# columns, a trigger, a property graph and a PL/SQL package; hybrid search creates views.
GRANTS = [
    "create session",
    "create table",
    "create view",
    "create sequence",
    "create trigger",
    "create procedure",
    "create property graph",
    "create mining model",
]


def main() -> None:
    password = os.environ.get("ORACLE_PWD")
    if not password:
        sys.exit("Set ORACLE_PWD to the password you passed to docker run.")
    if '"' in password:
        sys.exit("ORACLE_PWD must not contain a double quote.")
    dsn = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
    user = os.environ.get("ORACLE_USER", "quickstart").upper()
    if not user.isidentifier() or user.startswith("_"):
        sys.exit("ORACLE_USER must be a plain name: letters, digits and underscores.")

    admin = wait_for_database(dsn, password)
    create_user(admin, user, password)
    admin.close()

    conn = oracledb.connect(user=user, password=password, dsn=dsn)
    load_model(conn)
    print(f"Ready. Log in as {user} at {dsn}.")


def wait_for_database(dsn: str, password: str) -> oracledb.Connection:
    """Retry for a while: a fresh container needs a minute or two before it accepts logins."""
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        try:
            conn = oracledb.connect(user="system", password=password, dsn=dsn)
            print(f"Connected to {dsn}: Oracle Database {conn.version}")
            return conn
        except oracledb.Error as exc:
            if time.monotonic() > deadline:
                sys.exit(f"Could not connect to {dsn} as SYSTEM after {WAIT_SECONDS}s: {exc}")
            # The code tells a database that is still starting (DPY-6005, ORA-01109, and
            # ORA-01017 for a few seconds) from a wrong password (ORA-01017 that stays).
            print(f"Waiting for the database ({exc.args[0].full_code}) ...")
            time.sleep(5)


def pick_tablespace(cur: oracledb.Cursor) -> str:
    """Return a tablespace that can hold VECTOR columns (they need automatic segment space)."""
    cur.execute(
        """select property_value from database_properties
           where property_name = 'DEFAULT_PERMANENT_TABLESPACE'"""
    )
    default = cur.fetchone()[0]
    cur.execute(
        "select segment_space_management from dba_tablespaces where tablespace_name = :t",
        t=default,
    )
    if cur.fetchone()[0] == "AUTO":
        return default

    # The Lite image only has SYSTEM, which cannot hold VECTOR columns. Add a data file next
    # to SYSAUX, whose location we can read from the database.
    name = "QS_DATA"
    cur.execute("select count(*) from dba_tablespaces where tablespace_name = :t", t=name)
    if cur.fetchone()[0] == 0:
        cur.execute("select file_name from dba_data_files where tablespace_name = 'SYSAUX'")
        sysaux_file = cur.fetchone()[0]
        datafile = sysaux_file.rsplit("/", 1)[0] + "/qs_data01.dbf"
        cur.execute(
            f"create tablespace {name} datafile '{datafile}' size 100m "
            "autoextend on next 100m maxsize 2g"
        )
        print(f"Created tablespace {name} ({datafile}) because {default} cannot hold vectors.")
    return name


def create_user(admin: oracledb.Connection, user: str, password: str) -> None:
    with admin.cursor() as cur:
        tablespace = pick_tablespace(cur)
        cur.execute("select count(*) from dba_users where username = :u", u=user)
        if cur.fetchone()[0] == 0:
            cur.execute(f'create user {user} identified by "{password}"')
            print(f"Created user {user}.")
        else:
            # Keep ORACLE_PWD as the single source of truth for the password.
            cur.execute(f'alter user {user} identified by "{password}"')
            print(f"User {user} exists; password reset to ORACLE_PWD.")
        cur.execute(f"alter user {user} default tablespace {tablespace}")
        cur.execute(f"alter user {user} quota unlimited on {tablespace}")
        for grant in GRANTS:
            cur.execute(f"grant {grant} to {user}")


def model_zip() -> Path:
    """Download the model zip once into the system temp directory."""
    path = Path(tempfile.gettempdir()) / "oracle-quickstart" / "all_MiniLM_L12_v2_augmented.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and zipfile.is_zipfile(path):
        print(f"Using cached model download: {path}")
        return path
    print("Downloading the embedding model (about 117 MB) ...")
    partial = path.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, partial)
    partial.replace(path)
    return path


def load_model(conn: oracledb.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select count(*) from user_mining_models where model_name = :m", m=MODEL_NAME)
        if cur.fetchone()[0]:
            print(f"Model {MODEL_NAME} is already loaded.")
            return
        with zipfile.ZipFile(model_zip()) as archive:
            model_bytes = archive.read(MODEL_FILE_IN_ZIP)
        started = time.monotonic()
        cur.setinputsizes(data=oracledb.DB_TYPE_BLOB)
        cur.execute(
            "begin dbms_vector.load_onnx_model(:name, :data, json(:meta)); end;",
            name=MODEL_NAME,
            data=model_bytes,
            meta=json.dumps(MODEL_METADATA),
        )
        print(f"Loaded model {MODEL_NAME} in {time.monotonic() - started:.1f}s.")


if __name__ == "__main__":
    main()
