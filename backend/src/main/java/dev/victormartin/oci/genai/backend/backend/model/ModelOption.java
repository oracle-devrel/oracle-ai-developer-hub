package dev.victormartin.oci.genai.backend.backend.model;

import java.util.List;
import java.util.Map;

/**
 * UI/API-friendly model option, resolved to an actual OCI model OCID when available.
 */
public record ModelOption(
        String ocid,                 // management model OCID to call in OnDemand mode
        String displayName,          // e.g., "cohere.command-a-03-2025"
        String provider,             // "cohere", "google", "meta", ...
        String version,
        List<String> tasks,          // chat, summarize, text, embed, rerank
        List<String> modes,          // ON_DEMAND, DEDICATED
        Integer contextTokens,
        Map<String, Integer> maxOutputTokens, // {"onDemand": 4000, "dedicated": null}
        List<String> notes            // e.g., ["external_hosting","approval_required"]
) {}
