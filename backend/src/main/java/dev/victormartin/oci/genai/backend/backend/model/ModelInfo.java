package dev.victormartin.oci.genai.backend.backend.model;

import java.util.List;
import java.util.Map;

/**
 * LLM-parseable model descriptor loaded from classpath model_catalog.json
 */
public record ModelInfo(
        String id,
        String provider,
        String family,
        List<String> tasks,      // e.g. ["chat","summarize","text","embed","rerank"]
        List<String> modes,      // ["ON_DEMAND","DEDICATED"]
        List<String> regions,    // oci region identifiers e.g. "us-chicago-1"
        Integer contextTokens,   // max context window if known
        Map<String, Integer> maxOutputTokens, // keys: "onDemand","dedicated"
        Integer dim,             // embedding dimension if applicable
        List<String> notes       // tags like ["external_hosting","approval_required"]
) {}
