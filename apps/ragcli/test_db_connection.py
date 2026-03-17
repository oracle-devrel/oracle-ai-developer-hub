#!/usr/bin/env python3
"""Test script to connect to Oracle DB and read from DOCUMENTS table."""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ragcli.config.config_manager import load_config
    from ragcli.database.oracle_client import OracleClient

    print("Loading config...")
    config = load_config()
    print("Config loaded successfully.")

    print("Creating OracleClient...")
    client = OracleClient(config)
    print("OracleClient created.")

    print("Getting connection...")
    conn = client.get_connection()
    print("Connection acquired.")

    cursor = conn.cursor()

    # Test read from DOCUMENTS table
    print("Executing query...")
    cursor.execute("SELECT COUNT(*) FROM DOCUMENTS")
    count = cursor.fetchone()[0]
    print(f"SUCCESS: DOCUMENTS table has {count} rows.")

    cursor.close()
    client.close()
    print("Connection closed. Test completed successfully.")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
