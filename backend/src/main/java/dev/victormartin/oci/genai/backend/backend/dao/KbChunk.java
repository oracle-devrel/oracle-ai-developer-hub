package dev.victormartin.oci.genai.backend.backend.dao;

/**
 * Minimal KB chunk DTO returned from vector search.
 */
public record KbChunk(
        long chunkId,
        String docId,
        String title,
        String uri,
        String text,
        String sourceMeta,
        int chunkIx,
        String tenantId
) {}
