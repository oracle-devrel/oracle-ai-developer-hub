package dev.victormartin.oci.genai.backend.backend.service;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

import javax.sql.DataSource;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;

import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.EmbedTextDetails;
import com.oracle.bmc.generativeaiinference.model.OnDemandServingMode;
import com.oracle.bmc.generativeaiinference.requests.EmbedTextRequest;
import com.oracle.bmc.generativeaiinference.responses.EmbedTextResponse;
import com.oracle.bmc.model.BmcException;

import dev.victormartin.oci.genai.backend.backend.dao.KbChunk;
import dev.victormartin.oci.genai.backend.backend.dto.RagQuestionDto;

/**
 * Retrieval service:
 * 1) Embed question
 * 2) Vector search top-k (filters by tenant/doc/tags) [NOTE: requires Oracle AI Database VECTOR SQL]
 * 3) Assemble prompt with citations
 * 4) Call chat (delegated to OCIGenAIService)
 */
@Service
public class RagService {

    private static final Logger log = LoggerFactory.getLogger(RagService.class);

    private final GenAiInferenceClientService inferenceClientService;
    private final OCIGenAIService chatService;
    private final Environment env;
    private final DataSource dataSource;

    public RagService(GenAiInferenceClientService inferenceClientService,
                      OCIGenAIService chatService,
                      Environment env,
                      DataSource dataSource) {
        this.inferenceClientService = inferenceClientService;
        this.chatService = chatService;
        this.env = env;
        this.dataSource = dataSource;
    }

    public String answerWithRag(RagQuestionDto req) {
        String tenantId = Objects.requireNonNullElse(req.tenantId(), "default");
        int k = Objects.requireNonNullElse(req.topK(), 5);
        String modelId = req.modelId() != null ? req.modelId() : env.getProperty("genai.chat_model_id");

        // 1) Embed the question (OnDemand path by default)
        List<Float> qEmbed = embedQuestion(req.question());

        // 2) Retrieve top-k chunks from Oracle AI Database
        List<KbChunk> topk = topK(tenantId, qEmbed, req.docIds(), req.tags(), k, req.question());

        // 3) Assemble prompt with citations
        String prompt = assemblePrompt(req.question(), topk);

        // 4) Call chat model (Command A recommended)
        return chatService.resolvePrompt(prompt, modelId, false, false);
    }

    private List<Float> embedQuestion(String question) {
        String compartmentId = env.getProperty("genai.compartment_id");
        String configured = env.getProperty("genai.embed_model_id");
        // Fallback candidates known to be available in most regions
        List<String> candidates = new ArrayList<>();
        if (configured != null && !configured.isBlank()) {
            candidates.add(configured);
        }
        candidates.add("cohere.embed-english-v3.0");
        candidates.add("cohere.embed-multilingual-v3.0");
        candidates.add("cohere.embed-english-light-v3.0");

        BmcException last404 = null;
        RuntimeException lastOther = null;

        for (String modelId : candidates) {
            try {
                return embedWithModel(question, compartmentId, modelId);
            } catch (BmcException e) {
                if (e.getStatusCode() == 404) {
                    log.warn("Embedding model not found in region for id {} (404). Trying next candidate.", modelId);
                    last404 = e;
                    continue;
                }
                lastOther = new RuntimeException("EmbedText failed for modelId " + modelId + " with status " + e.getStatusCode(), e);
            } catch (RuntimeException e) {
                lastOther = e;
            }
        }
        if (lastOther != null) {
            throw lastOther;
        }
        if (last404 != null) {
            throw new IllegalStateException("No available embedding model found. Tried: " + String.join(", ", candidates), last404);
        }
        throw new IllegalStateException("No available embedding model found. Tried: " + String.join(", ", candidates));
    }

    private List<Float> embedWithModel(String question, String compartmentId, String modelId) {
        GenerativeAiInferenceClient client = inferenceClientService.getClient();

        EmbedTextDetails details = EmbedTextDetails.builder()
                .inputs(List.of(question))
                .servingMode(OnDemandServingMode.builder().modelId(modelId).build())
                .compartmentId(compartmentId)
                .isEcho(false)
                .build();

        EmbedTextResponse resp = client.embedText(EmbedTextRequest.builder()
                .embedTextDetails(details)
                .build());
        if (resp.getEmbedTextResult() == null
                || resp.getEmbedTextResult().getEmbeddings() == null
                || resp.getEmbedTextResult().getEmbeddings().isEmpty()) {
            throw new IllegalStateException("No embedding returned for question");
        }

        // The SDK may return either a list of floats directly or an object with getValues().
        Object first = resp.getEmbedTextResult().getEmbeddings().get(0);
        if (first instanceof List) {
            @SuppressWarnings("unchecked")
            List<Float> vals = (List<Float>) first;
            try { log.info("RAG.embed: model={} dim={}", modelId, (vals != null ? vals.size() : -1)); } catch (Exception ignore) {}
            return vals;
        }
        try {
            @SuppressWarnings("unchecked")
            List<Float> vals = (List<Float>) first.getClass().getMethod("getValues").invoke(first);
            try { log.info("RAG.embed: model={} dim={}", modelId, (vals != null ? vals.size() : -1)); } catch (Exception ignore) {}
            return vals;
        } catch (Exception e) {
            throw new IllegalStateException("Unsupported embedding element type: " + first.getClass(), e);
        }
    }

    /**
     * Perform a vector top-k search.
     * NOTE: This requires Oracle AI Database VECTOR support and proper binding of the query vector.
     * and use appropriate binding for vector values (e.g. JSON array -> VECTOR).
     */
    private List<KbChunk> topK(String tenantId, List<Float> qEmbed, List<String> docIds, List<String> tags, int k, String question) {
        List<KbChunk> out = new ArrayList<>();

        String sql =
                "SELECT c.id AS chunk_id, c.doc_id, d.title, d.uri, c.text, c.source_meta, c.chunk_ix, c.tenant_id " +
                "FROM kb_embeddings e " +
                "JOIN kb_chunks c ON c.id = e.chunk_id " +
                "JOIN kb_documents d ON d.doc_id = c.doc_id " +
                "WHERE c.tenant_id = ? " +
                "FETCH FIRST ? ROWS ONLY";

        try (Connection conn = dataSource.getConnection()) {
            boolean usedVector = false;

            // 1) Try Oracle AI Database VECTOR path when we have a query embedding
            if (qEmbed != null && !qEmbed.isEmpty()) {
                // Build JSON array for TO_VECTOR(?)
                StringBuilder vsb = new StringBuilder();
                vsb.append('[');
                for (int i = 0; i < qEmbed.size(); i++) {
                    if (i > 0) vsb.append(',');
                    Float v = qEmbed.get(i);
                    if (v == null || v.isNaN() || v.isInfinite()) {
                        vsb.append('0');
                    } else {
                        vsb.append(v.toString());
                    }
                }
                vsb.append(']');
                String qvecJson = vsb.toString();

                StringBuilder sqlVec = new StringBuilder();
                sqlVec.append("SELECT c.id AS chunk_id, c.doc_id, d.title, d.uri, c.text, c.source_meta, c.chunk_ix, c.tenant_id, ");
                sqlVec.append("VECTOR_DISTANCE(e.embedding, TO_VECTOR(?)) AS dist ");
                sqlVec.append("FROM kb_embeddings e ");
                sqlVec.append("JOIN kb_chunks c ON c.id = e.chunk_id ");
                sqlVec.append("JOIN kb_documents_dv d ON d.doc_id = c.doc_id ");
                sqlVec.append("WHERE c.tenant_id = ? ");
                if (docIds != null && !docIds.isEmpty()) {
                    sqlVec.append("AND c.doc_id IN (");
                    for (int i = 0; i < docIds.size(); i++) {
                        if (i > 0) sqlVec.append(',');
                        sqlVec.append('?');
                    }
                    sqlVec.append(") ");
                }
                // Optional: add tags filter via JSON_EXISTS(d.tags_json, '$[*]?(@ like_regex "...")')
                sqlVec.append("ORDER BY dist ASC FETCH FIRST ? ROWS ONLY");

                try (PreparedStatement ps = conn.prepareStatement(sqlVec.toString())) {
                    int idx = 1;
                    ps.setString(idx++, qvecJson);
                    ps.setString(idx++, tenantId);
                    if (docIds != null && !docIds.isEmpty()) {
                        for (String id : docIds) {
                            ps.setString(idx++, id);
                        }
                    }
                    ps.setInt(idx++, k);

                    try (ResultSet rs = ps.executeQuery()) {
                        while (rs.next()) {
                            out.add(new KbChunk(
                                    rs.getLong("chunk_id"),
                                    rs.getString("doc_id"),
                                    rs.getString("title"),
                                    rs.getString("uri"),
                                    rs.getString("text"),
                                    rs.getString("source_meta"),
                                    rs.getInt("chunk_ix"),
                                    rs.getString("tenant_id")
                            ));
                        }
                    }
                    usedVector = !out.isEmpty();
                } catch (SQLException e1) {
                    log.debug("Vector search attempt failed ({}). Will fallback to text search: {}", e1.getClass().getSimpleName(), e1.getMessage());
                    out.clear();
                    usedVector = false;
                }
            }

            // 2) Fallback: lightweight text search over kb_chunks to avoid empty context
            if (!usedVector) {
                // Extract simple tokens from question
                List<String> tokens = new ArrayList<>();
                if (question != null) {
                    String q = question.toLowerCase();
                    for (String t : q.split("\\W+")) {
                        if (t != null && t.length() >= 3) {
                            tokens.add(t);
                        }
                        if (tokens.size() >= 5) break; // cap tokens
                    }
                }

                if (!tokens.isEmpty()) {
                    StringBuilder regex = new StringBuilder();
                    regex.append('(');
                    for (int i = 0; i < tokens.size(); i++) {
                        if (i > 0) regex.append('|');
                        String safe = tokens.get(i).replaceAll("[^a-z0-9]", "");
                        if (!safe.isEmpty()) {
                            regex.append(safe);
                        }
                    }
                    regex.append(')');

                    StringBuilder sqlLike = new StringBuilder();
                    sqlLike.append("SELECT c.id AS chunk_id, c.doc_id, d.title, d.uri, c.text, c.source_meta, c.chunk_ix, c.tenant_id ");
                    sqlLike.append("FROM kb_chunks c ");
                    sqlLike.append("JOIN kb_documents_dv d ON d.doc_id = c.doc_id ");
                    sqlLike.append("WHERE c.tenant_id = ? ");
                    if (docIds != null && !docIds.isEmpty()) {
                        sqlLike.append("AND c.doc_id IN (");
                        for (int i = 0; i < docIds.size(); i++) {
                            if (i > 0) sqlLike.append(',');
                            sqlLike.append('?');
                        }
                        sqlLike.append(") ");
                    }
                    sqlLike.append("AND REGEXP_LIKE(c.text, ?, 'i') ");
                    sqlLike.append("FETCH FIRST ? ROWS ONLY");

                    try (PreparedStatement ps = conn.prepareStatement(sqlLike.toString())) {
                        int idx = 1;
                        ps.setString(idx++, tenantId);
                        if (docIds != null && !docIds.isEmpty()) {
                            for (String id : docIds) {
                                ps.setString(idx++, id);
                            }
                        }
                        ps.setString(idx++, regex.toString());
                        ps.setInt(idx++, k);

                        try (ResultSet rs = ps.executeQuery()) {
                            while (rs.next()) {
                                out.add(new KbChunk(
                                        rs.getLong("chunk_id"),
                                        rs.getString("doc_id"),
                                        rs.getString("title"),
                                        rs.getString("uri"),
                                        rs.getString("text"),
                                        rs.getString("source_meta"),
                                        rs.getInt("chunk_ix"),
                                        rs.getString("tenant_id")
                                ));
                            }
                        }
                    } catch (SQLException e2) {
                        log.warn("Fallback text search failed ({}): {}", e2.getClass().getSimpleName(), e2.getMessage());
                    }
                }
                if (out.isEmpty()) {
                    StringBuilder sqlAny = new StringBuilder();
                    sqlAny.append("SELECT c.id AS chunk_id, c.doc_id, d.title, d.uri, c.text, c.source_meta, c.chunk_ix, c.tenant_id ");
                    sqlAny.append("FROM kb_chunks c ");
                    sqlAny.append("JOIN kb_documents_dv d ON d.doc_id = c.doc_id ");
                    sqlAny.append("WHERE c.tenant_id = ? ");
                    if (docIds != null && !docIds.isEmpty()) {
                        sqlAny.append("AND c.doc_id IN (");
                        for (int i = 0; i < docIds.size(); i++) {
                            if (i > 0) sqlAny.append(',');
                            sqlAny.append('?');
                        }
                        sqlAny.append(") ");
                    }
                    sqlAny.append("ORDER BY c.id DESC FETCH FIRST ? ROWS ONLY");

                    try (PreparedStatement ps = conn.prepareStatement(sqlAny.toString())) {
                        int idx = 1;
                        ps.setString(idx++, tenantId);
                        if (docIds != null && !docIds.isEmpty()) {
                            for (String id : docIds) {
                                ps.setString(idx++, id);
                            }
                        }
                        ps.setInt(idx++, k);

                        try (ResultSet rs = ps.executeQuery()) {
                            while (rs.next()) {
                                out.add(new KbChunk(
                                        rs.getLong("chunk_id"),
                                        rs.getString("doc_id"),
                                        rs.getString("title"),
                                        rs.getString("uri"),
                                        rs.getString("text"),
                                        rs.getString("source_meta"),
                                        rs.getInt("chunk_ix"),
                                        rs.getString("tenant_id")
                                ));
                            }
                        }
                    } catch (SQLException e3) {
                        log.warn("Fallback any-chunk retrieval failed ({}): {}", e3.getClass().getSimpleName(), e3.getMessage());
                    }
                }
            }

            log.info("RAG.topK tenant={} k={} docIds={} usedVectorCandidates={} results={}",
                    tenantId,
                    k,
                    (docIds == null ? 0 : docIds.size()),
                    (qEmbed != null && !qEmbed.isEmpty()),
                    out.size());

        } catch (SQLException outer) {
            log.warn("DB connection failed during retrieval: {}", outer.getMessage());
        }
        return out;
    }

    private String assemblePrompt(String question, List<KbChunk> snippets) {
        StringBuilder sb = new StringBuilder();
        sb.append("SYSTEM:\n");
        sb.append("You are an assistant that answers strictly using the provided CONTEXT.\n");
        sb.append("If the answer is not in CONTEXT, say \"I don't know from the provided context.\"\n\n");
        sb.append("CONTEXT:\n");
        int i = 1;
        for (KbChunk s : snippets) {
            String source = s.uri() != null ? s.uri() : s.docId();
            sb.append("[").append(i).append("] ").append(s.text()).append(" (source: ").append(source).append(")\n");
            i++;
        }
        sb.append("\nUSER:\n").append(question).append("\n\n");
        sb.append("ASSISTANT (rules):\n");
        sb.append("- Answer in 3-5 bullets; include inline citations like [1], [2]\n");
        sb.append("- If insufficient context, reply: \"I don't know from the provided context.\"\n");
        return sb.toString();
    }
}
