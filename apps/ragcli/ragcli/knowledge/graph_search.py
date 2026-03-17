"""Graph search over knowledge graph entities and relationships."""
import json
from typing import Dict, List

from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class GraphSearch:
    """Search the knowledge graph using vector similarity and graph traversal."""

    def __init__(self, conn, config: dict):
        self.conn = conn
        self.max_hops = config.get("knowledge_graph", {}).get("max_hops", 2)

    def find_entities_by_embedding(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict]:
        """Find entities by vector similarity on KG_ENTITIES.embedding."""
        sql = """
            SELECT entity_id, name, entity_type,
                   VECTOR_DISTANCE(embedding, TO_VECTOR(:v_emb), COSINE) AS distance
            FROM KG_ENTITIES
            ORDER BY distance ASC
            FETCH FIRST :v_top_k ROWS ONLY
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                sql,
                {"v_emb": json.dumps(query_embedding), "v_top_k": top_k},
            )
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "entity_id": row[0],
                    "name": row[1],
                    "entity_type": row[2],
                    "distance": row[3],
                }
            )
        return results

    def get_chunks_for_entities(self, entity_ids: List[str]) -> List[str]:
        """Get chunk IDs linked to the given entities via KG_ENTITY_CHUNKS."""
        if not entity_ids:
            return []

        placeholders = ", ".join(f":e{i}" for i in range(len(entity_ids)))
        sql = f"""
            SELECT DISTINCT chunk_id
            FROM KG_ENTITY_CHUNKS
            WHERE entity_id IN ({placeholders})
        """
        bind_vars = {f"e{i}": eid for i, eid in enumerate(entity_ids)}

        with self.conn.cursor() as cursor:
            cursor.execute(sql, bind_vars)
            rows = cursor.fetchall()

        return [row[0] for row in rows]

    def _expand_entity(
        self, entity_id: str, max_hops: int
    ) -> List[Dict]:
        """Expand an entity through KG_RELATIONSHIPS up to max_hops."""
        visited = set()
        frontier = [entity_id]
        related = []

        for hop in range(max_hops):
            if not frontier:
                break
            next_frontier = []
            placeholders = ", ".join(f":f{i}" for i in range(len(frontier)))
            sql = f"""
                SELECT r.target_entity_id, e.name, e.entity_type, r.relationship_type
                FROM KG_RELATIONSHIPS r
                JOIN KG_ENTITIES e ON e.entity_id = r.target_entity_id
                WHERE r.source_entity_id IN ({placeholders})
                  AND r.target_entity_id NOT IN (
                    SELECT column_value FROM TABLE(SYS.ODCIVARCHAR2LIST({
                        ", ".join(f":v{i}" for i in range(len(visited))) or "NULL"
                    }))
                  )
            """
            bind_vars = {f"f{i}": fid for i, fid in enumerate(frontier)}
            # Only add visited binds if we have visited entities
            if visited:
                for i, vid in enumerate(visited):
                    bind_vars[f"v{i}"] = vid

            with self.conn.cursor() as cursor:
                cursor.execute(sql, bind_vars)
                rows = cursor.fetchall()

            for row in rows:
                target_id, name, etype, rel_type = row
                if target_id not in visited:
                    related.append(
                        {
                            "entity_id": target_id,
                            "name": name,
                            "entity_type": etype,
                            "relationship": rel_type,
                            "hop": hop + 1,
                        }
                    )
                    next_frontier.append(target_id)

            visited.update(frontier)
            frontier = next_frontier

        return related

    def subgraph_for_query(
        self, query_embedding: List[float], top_k: int = 10
    ) -> Dict:
        """Build a subgraph for a query: seed entities, expand hops, collect chunks."""
        seed_entities = self.find_entities_by_embedding(query_embedding, top_k=top_k)
        logger.debug("Found %d seed entities for query", len(seed_entities))

        all_entities = list(seed_entities)
        all_entity_ids = [e["entity_id"] for e in seed_entities]

        # Expand each seed entity through relationships
        for entity in seed_entities:
            related = self._expand_entity(entity["entity_id"], self.max_hops)
            for rel in related:
                if rel["entity_id"] not in all_entity_ids:
                    all_entities.append(rel)
                    all_entity_ids.append(rel["entity_id"])

        # Collect chunk IDs for all discovered entities
        chunk_ids = self.get_chunks_for_entities(all_entity_ids)
        logger.debug(
            "Subgraph: %d entities, %d chunks", len(all_entities), len(chunk_ids)
        )

        return {
            "entities": all_entities,
            "chunk_ids": chunk_ids,
            "seed_count": len(seed_entities),
            "total_entities": len(all_entities),
        }
