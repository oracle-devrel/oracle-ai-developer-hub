package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.HtmlUtils;

import com.oracle.bmc.model.BmcException;

import dev.victormartin.oci.genai.backend.backend.dao.Answer;
import dev.victormartin.oci.genai.backend.backend.dao.SummaryRequest;
import dev.victormartin.oci.genai.backend.backend.data.Conversation;
import dev.victormartin.oci.genai.backend.backend.data.ConversationRepository;
import dev.victormartin.oci.genai.backend.backend.data.InteractionEvent;
import dev.victormartin.oci.genai.backend.backend.data.InteractionEventRepository;
import dev.victormartin.oci.genai.backend.backend.data.Message;
import dev.victormartin.oci.genai.backend.backend.data.MessageRepository;
import dev.victormartin.oci.genai.backend.backend.service.MemoryService;
import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;

@RestController
public class SummaryController {
    Logger logger = LoggerFactory.getLogger(SummaryController.class);

    @Value("${genai.summarization_model_id}")
    String summarizationModelId;

    @Autowired
    OCIGenAIService ociGenAIService;

    @Autowired
    private ConversationRepository conversationRepository;

    @Autowired
    private MessageRepository messageRepository;

    @Autowired
    private InteractionEventRepository interactionEventRepository;

    @Autowired
    private MemoryService memoryService;

    @PostMapping("/api/genai/summary")
    public Answer postSummaryText(@RequestBody SummaryRequest summaryRequest,
                                  @RequestHeader("conversationID") String conversationId,
                                  @RequestHeader("modelId") String modelId) {
        logger.info("postSummaryText()");
        String contentEscaped = HtmlUtils.htmlEscape(summaryRequest.content());
        String activeModel = (modelId == null || modelId.isBlank()) ? summarizationModelId : modelId;
        logger.info("contentEscaped: {}...", contentEscaped.substring(0, Math.min(50, contentEscaped.length())));

        // Ensure conversation exists (tenant=default)
        try {
            if (!conversationRepository.existsById(conversationId)) {
                conversationRepository.save(new Conversation(conversationId, "default", null, "active"));
            }
        } catch (Exception e) {
            logger.warn("Failed to ensure conversation exists: {}", e.getMessage());
        }

        long t0 = System.nanoTime();
        try {
            // user message (what the user sent to be summarized)
            Message mUser = new Message(UUID.randomUUID().toString(), conversationId, "user", contentEscaped);
            messageRepository.save(mUser);

            // call model (capture usage if available)
            dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService.ModelResponse modelResp =
                ociGenAIService.resolvePromptWithUsage(contentEscaped, activeModel, false, true);
            String summaryText = modelResp.getContent();

            // assistant message (summary produced)
            Message mAsst = new Message(UUID.randomUUID().toString(), conversationId, "assistant", summaryText);
            messageRepository.save(mAsst);
            // update rolling memory
            memoryService.updateRollingSummary(conversationId);

            // telemetry
            long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
            InteractionEvent ev = new InteractionEvent("default", "summary_text", activeModel);
            ev.setLatencyMs(latencyMs);
            if (modelResp.getTokensIn() != null) {
                ev.setTokensIn(modelResp.getTokensIn().longValue());
            }
            if (modelResp.getTokensOut() != null) {
                ev.setTokensOut(modelResp.getTokensOut().longValue());
            }
            if (modelResp.getCost() != null) {
                ev.setCostEst(java.math.BigDecimal.valueOf(modelResp.getCost()));
            }
            interactionEventRepository.save(ev);

            Answer answer = new Answer();
            answer.setContent(summaryText);
            answer.setErrorMessage("");
            return answer;

        } catch (BmcException e) {
            String unmodifiedMessage = e.getUnmodifiedMessage();
            int statusCode = e.getStatusCode();
            String errorMessage = statusCode + " " + unmodifiedMessage;
            logger.error(errorMessage);

            try {
                long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
                InteractionEvent ev = new InteractionEvent("default", "summary_text", activeModel);
                ev.setLatencyMs(latencyMs);
                interactionEventRepository.save(ev);
            } catch (Exception ignore) {}

            return new Answer("", errorMessage);
        } catch (Exception e) {
            String errorMessage = e.getLocalizedMessage();
            logger.error(errorMessage);

            try {
                long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
                InteractionEvent ev = new InteractionEvent("default", "summary_text", activeModel);
                ev.setLatencyMs(latencyMs);
                interactionEventRepository.save(ev);
            } catch (Exception ignore) {}

            return new Answer("", errorMessage);
        }
    }
}
