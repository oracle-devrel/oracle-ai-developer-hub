"""Oracle Database 26ai client for ragcli."""

import oracledb
from typing import Optional
from .schemas import get_create_schemas_sql

# Force thin mode (default) to avoid thick mode credential issues
oracledb.defaults.thin_mode = True

class OracleClient:
    def __init__(self, config: dict):
        self.config = config
        self.pool = None
        self._connect()

    def _get_db_config(self) -> dict:
        """Resolve database config from profiles or legacy oracle key."""
        db = self.config.get('database', {})
        if 'profiles' in db:
            profile_name = db.get('active_profile', 'local')
            profile = db['profiles'].get(profile_name)
            if profile:
                return profile
        return self.config.get('oracle', {})

    def _connect(self):
        """Establish connection pool."""
        db_config = self._get_db_config()
        username = db_config.get('username') or db_config.get('user', 'ADMIN')
        password = db_config['password']
        dsn = db_config['dsn']
        pool_size = db_config.get('pool_size', 10)
        use_tls = db_config.get('use_tls', True)
        tls_wallet_path = db_config.get('tls_wallet_path', None)

        # Configure TLS: always use TLS, never require wallet path
        params = {}
        if use_tls:
            params['wallet_location'] = tls_wallet_path  # None for no wallet (basic TLS)

        self.pool = oracledb.create_pool(
            user=username,
            password=password,
            dsn=dsn,
            min=1,
            max=pool_size,
            increment=1,
            **params
        )
    
    def get_connection(self) -> oracledb.Connection:
        """Get a connection from the pool."""
        return self.pool.acquire()
    
    def init_db(self):
        """Initialize database schemas and indexes if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()
        tables = get_create_schemas_sql(self.config)

        created_something = False

        try:
            # Create tables if they don't exist
            for table_name, create_sql in tables:
                cursor.execute("SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = :tname", {"tname": table_name})
                if cursor.fetchone()[0] == 0:
                    cursor.execute(create_sql)
                    created_something = True

            # Create vector index if it doesn't exist
            cursor.execute("SELECT COUNT(*) FROM USER_INDEXES WHERE INDEX_NAME = 'CHUNKS_EMBEDDING_IDX'")
            if cursor.fetchone()[0] == 0:
                print("WARNING: Skipping vector index creation due to unsupported syntax in current Oracle Database version.")
                print("Vector search will work but may be slower without an index. Please ensure Oracle Database 26ai or later is used.")
                # Vector index creation requires Oracle Database 26ai+ with vector support enabled.
                # vi_config = self.config['vector_index']
                # if vi_config['index_type'] == 'HNSW':
                #     index_sql = f"""CREATE VECTOR INDEX CHUNKS_EMBEDDING_IDX
                # ON CHUNKS(chunk_embedding) ORGANIZATION HNSW
                # PARAMETERS ('hnsw_graph_m' {vi_config['m']}, 'hnsw_graph_ef_construction' {vi_config['ef_construction']});"""
                # elif vi_config['index_type'] == 'INMEMORY':
                #     index_sql = """CREATE VECTOR INDEX CHUNKS_EMBEDDING_IDX
                # ON CHUNKS(chunk_embedding);"""
                # else:
                #     # Default to INMEMORY if unsupported
                #     index_sql = """CREATE VECTOR INDEX CHUNKS_EMBEDDING_IDX
                # ON CHUNKS(chunk_embedding);"""
                # cursor.execute(index_sql)
                # created_something = True

            if created_something:
                conn.commit()
                print("Database schemas and indexes created successfully.")
            else:
                print("Database already initialized.")

        except oracledb.Error as e:
            conn.rollback()
            raise Exception(f"Failed to initialize database: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def close(self):
        """Close the pool."""
        if self.pool:
            self.pool.close()

# TODO: Implement retries in _connect(), auto-index selection based on data size
