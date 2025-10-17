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

import dev.victormartin.oci.genai.backend.backend.dao.KbChunk;
import dev.victormartin.oci.genai.backend.backend.dto.RagQuestionDto;

/**
 * Retrieval service:
 * 1) Embed question
 * 2) Vector search top-k (filters by tenant/doc/tags) [NOTE: requires Oracle DB 23ai VECTOR SQL]
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

        // 2) Retrieve top-k chunks from Oracle DB 23ai
        List<KbChunk> topk = topK(tenantId, qEmbed, req.docIds(), req.tags(), k);

        // 3) Assemble prompt with citations
        String prompt = assemblePrompt(req.question(), topk);

        // 4) Call chat model (Command A recommended)
        return chatService.resolvePrompt(prompt, modelId, false, false);
    }

    private List<Float> embedQuestion(String question) {
        String compartmentId = env.getProperty("genai.compartment_id");
        String embedModelId = env.getProperty("genai.embed_model_id", "cohere.embed-english-3"); // default
        GenerativeAiInferenceClient client = inferenceClientService.getClient();

        EmbedTextDetails details = EmbedTextDetails.builder()
                .inputs(List.of(question))
                .servingMode(OnDemandServingMode.builder().modelId(embedModelId).build())
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
            return vals;
        }
        try {
            @SuppressWarnings("unchecked")
            List<Float> vals = (List<Float>) first.getClass().getMethod("getValues").invoke(first);
            return vals;
        } catch (Exception e) {
            throw new IllegalStateException("Unsupported embedding element type: " + first.getClass(), e);
        }
    }

    /**
     * Perform a vector top-k search.
     * NOTE: This requires Oracle Database 23ai VECTOR support and proper binding of the query vector.
     * The SQL below is a placeholder; replace VECTOR_DISTANCE(...) with the exact function for your DB version,
     * and use appropriate binding for vector values (e.g. JSON array -> VECTOR).
     */
    private List<KbChunk> topK(String tenantId, List<Float> qEmbed, List<String> docIds, List<String> tags, int k) {
        List<KbChunk> out = new ArrayList<>();

        // Fallback: if VECTOR SQL isn't configured yet, return empty list (chat will answer without context)
        String sql =
                "SELECT c.id AS chunk_id, c.doc_id, d.title, d.uri, c.text, c.source_meta, c.chunk_ix, c.tenant_id " +
                "FROM kb_embeddings e " +
                "JOIN kb_chunks c ON c.id = e.chunk_id " +
                "JOIN kb_documents d ON d.doc_id = c.doc_id " +
                "WHERE c.tenant_id = ? " +
                // Optional filters can be appended when implemented:
                // (docIds IN ...) and tags_json filters using JSON_EXISTS
                "FETCH FIRST ? ROWS ONLY";

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {

            ps.setString(1, tenantId);
            ps.setInt(2, k);

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
        } catch (SQLException e) {
            log.warn("Vector search not executed (falling back to zero-context): {}", e.getMessage());
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
