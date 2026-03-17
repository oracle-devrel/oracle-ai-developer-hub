"""Knowledge graph store backed by Oracle Database."""

import json
from typing import Dict, List, Optional

from ragcli.utils.helpers import generate_uuid
from ragcli.utils.logger import get_logger

logger = get_logger(__name__)


class GraphStore:
    """CRUD operations for knowledge graph entities and relationships in Oracle DB."""

    def __init__(self, conn):
        """Initialize with a database connection.

        Args:
            conn: An oracledb connection object.
        """
        self.conn = conn

    def upsert_entity(
        self,
        name: str,
        entity_type: str,
        description: str,
        embedding: Optional[List[float]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Insert a new entity or bump mention_count if it already exists.

        Lookup is case-insensitive on entity_name.

        Args:
            name: The entity name (e.g. "Python").
            entity_type: Category such as TECHNOLOGY, PERSON, ORG.
            description: Free-text description.
            embedding: Optional embedding vector.
            doc_id: Optional document ID where the entity was first seen.

        Returns:
            The entity_id (existing or newly generated).
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT entity_id FROM KG_ENTITIES
                   WHERE UPPER(entity_name) = UPPER(:1)""",
                [name],
            )
            row = cursor.fetchone()

            if row is not None:
                existing_id = row[0]
                cursor.execute(
                    """UPDATE KG_ENTITIES
                       SET mention_count = mention_count + 1
                       WHERE entity_id = :1""",
                    [existing_id],
                )
                self.conn.commit()
                logger.debug("Bumped mention_count for entity %s", existing_id)
                return existing_id

            entity_id = generate_uuid()
            if embedding is not None:
                cursor.execute(
                    """INSERT INTO KG_ENTITIES
                       (entity_id, entity_name, entity_type, description,
                        embedding, first_seen_doc)
                       VALUES (:1, :2, :3, :4, TO_VECTOR(:5), :6)""",
                    [entity_id, name, entity_type, description,
                     json.dumps(embedding), doc_id],
                )
            else:
                cursor.execute(
                    """INSERT INTO KG_ENTITIES
                       (entity_id, entity_name, entity_type, description,
                        first_seen_doc)
                       VALUES (:1, :2, :3, :4, :5)""",
                    [entity_id, name, entity_type, description, doc_id],
                )
        self.conn.commit()
        logger.debug("Created entity %s (%s)", entity_id, name)
        return entity_id

    def insert_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        description: str,
        chunk_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> str:
        """Insert a directed relationship between two entities.

        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.
            rel_type: Relationship label (e.g. USES, CONTAINS).
            description: Free-text description of the relationship.
            chunk_id: Optional originating chunk ID.
            document_id: Optional originating document ID.

        Returns:
            The generated rel_id.
        """
        rel_id = generate_uuid()
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO KG_RELATIONSHIPS
                   (rel_id, source_id, target_id, rel_type, description,
                    chunk_id, document_id)
                   VALUES (:1, :2, :3, :4, :5, :6, :7)""",
                [rel_id, source_id, target_id, rel_type, description,
                 chunk_id, document_id],
            )
        self.conn.commit()
        logger.debug("Created relationship %s: %s -[%s]-> %s",
                      rel_id, source_id, rel_type, target_id)
        return rel_id

    def link_entity_chunk(self, entity_id: str, chunk_id: str) -> None:
        """Idempotently link an entity to a chunk via MERGE.

        Args:
            entity_id: The entity to link.
            chunk_id: The chunk to link.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """MERGE INTO KG_ENTITY_CHUNKS tgt
                   USING (SELECT :1 AS entity_id, :2 AS chunk_id FROM DUAL) src
                   ON (tgt.entity_id = src.entity_id AND tgt.chunk_id = src.chunk_id)
                   WHEN NOT MATCHED THEN
                       INSERT (entity_id, chunk_id) VALUES (src.entity_id, src.chunk_id)""",
                [entity_id, chunk_id],
            )
        self.conn.commit()
        logger.debug("Linked entity %s to chunk %s", entity_id, chunk_id)

    def adjust_weight(
        self,
        rel_id: str,
        delta: float,
        floor: float = 0.1,
        ceiling: float = 5.0,
    ) -> None:
        """Adjust a relationship's weight, clamped between floor and ceiling.

        Args:
            rel_id: The relationship to adjust.
            delta: Amount to add (can be negative).
            floor: Minimum allowed weight.
            ceiling: Maximum allowed weight.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """UPDATE KG_RELATIONSHIPS
                   SET weight = GREATEST(:1, LEAST(:2, weight + :3))
                   WHERE rel_id = :4""",
                [floor, ceiling, delta, rel_id],
            )
        self.conn.commit()
        logger.debug("Adjusted weight for relationship %s by %+.2f", rel_id, delta)

    def get_entity_chunks(self, entity_id: str) -> List[str]:
        """Get all chunk IDs linked to an entity.

        Args:
            entity_id: The entity to query.

        Returns:
            List of chunk_id strings.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT chunk_id FROM KG_ENTITY_CHUNKS WHERE entity_id = :1",
                [entity_id],
            )
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    def get_entities_by_doc(self, document_id: str) -> List[Dict]:
        """Get all entities that have relationships in a given document.

        Args:
            document_id: The document ID to filter by.

        Returns:
            List of entity dicts with entity_id, entity_name, entity_type,
            description, and mention_count.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT DISTINCT e.entity_id, e.entity_name, e.entity_type,
                          e.description, e.mention_count
                   FROM KG_ENTITIES e
                   JOIN KG_RELATIONSHIPS r
                       ON e.entity_id = r.source_id OR e.entity_id = r.target_id
                   WHERE r.document_id = :1
                   ORDER BY e.mention_count DESC""",
                [document_id],
            )
            rows = cursor.fetchall()
        return [
            {
                "entity_id": row[0],
                "entity_name": row[1],
                "entity_type": row[2],
                "description": row[3],
                "mention_count": row[4],
            }
            for row in rows
        ]

    def find_related(self, entity_id: str, max_hops: int = 2) -> List[Dict]:
        """Multi-hop recursive traversal from a starting entity.

        Uses Oracle's recursive WITH (CONNECT BY alternative) to walk
        relationships up to max_hops deep.

        Args:
            entity_id: The starting entity ID.
            max_hops: Maximum traversal depth (default 2).

        Returns:
            List of dicts with rel_id, source_id, target_id, rel_type,
            weight, and hop_level.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """WITH RECURSIVE traversal (rel_id, source_id, target_id,
                                             rel_type, weight, hop_level) AS (
                       SELECT rel_id, source_id, target_id, rel_type, weight, 1
                       FROM KG_RELATIONSHIPS
                       WHERE source_id = :1
                   UNION ALL
                       SELECT r.rel_id, r.source_id, r.target_id,
                              r.rel_type, r.weight, t.hop_level + 1
                       FROM KG_RELATIONSHIPS r
                       JOIN traversal t ON r.source_id = t.target_id
                       WHERE t.hop_level < :2
                   )
                   SELECT DISTINCT rel_id, source_id, target_id,
                          rel_type, weight, hop_level
                   FROM traversal
                   ORDER BY hop_level, weight DESC""",
                [entity_id, max_hops],
            )
            rows = cursor.fetchall()
        return [
            {
                "rel_id": row[0],
                "source_id": row[1],
                "target_id": row[2],
                "rel_type": row[3],
                "weight": row[4],
                "hop_level": row[5],
            }
            for row in rows
        ]

    def delete_entities_for_chunks(self, chunk_ids: List[str]) -> int:
        """Remove entity-chunk links for the given chunks and clean up orphans.

        Deletes links from KG_ENTITY_CHUNKS, then removes any entities that
        no longer have any chunk links.

        Args:
            chunk_ids: List of chunk IDs to unlink.

        Returns:
            Number of orphaned entities deleted.
        """
        if not chunk_ids:
            return 0

        placeholders = ", ".join(f":{i + 1}" for i in range(len(chunk_ids)))
        with self.conn.cursor() as cursor:
            # Remove entity-chunk links
            cursor.execute(
                f"DELETE FROM KG_ENTITY_CHUNKS WHERE chunk_id IN ({placeholders})",
                chunk_ids,
            )
            logger.debug("Removed entity-chunk links for %d chunks", len(chunk_ids))

            # Delete orphaned entities (no remaining chunk links)
            cursor.execute(
                """DELETE FROM KG_ENTITIES
                   WHERE entity_id NOT IN (
                       SELECT DISTINCT entity_id FROM KG_ENTITY_CHUNKS
                   )"""
            )
            orphan_count = cursor.rowcount
        self.conn.commit()
        logger.debug("Deleted %d orphaned entities", orphan_count)
        return orphan_count
