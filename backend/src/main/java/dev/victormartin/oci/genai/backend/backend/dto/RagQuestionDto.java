package dev.victormartin.oci.genai.backend.backend.dto;

import java.util.List;

/**
 * Request payload for RAG questions.
 */
public record RagQuestionDto(
        String tenantId,
        String conversationId,
        String question,
        Integer topK,
        List<String> docIds,
        List<String> tags,
        String modelId,
        Params params
) {
    public record Params(
            Double temperature,
            Double topP,
            Integer topK,
            Integer maxTokens,
            Integer seed,
            String responseFormat // "TEXT" | "JSON_OBJECT"
    ) {}
}
