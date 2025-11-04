package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.simp.annotation.SendToUser;
import org.springframework.stereotype.Controller;
import org.springframework.web.util.HtmlUtils;

import com.oracle.bmc.model.BmcException;

import dev.victormartin.oci.genai.backend.backend.InvalidPromptRequest;
import dev.victormartin.oci.genai.backend.backend.dao.Answer;
import dev.victormartin.oci.genai.backend.backend.dao.Prompt;
import dev.victormartin.oci.genai.backend.backend.data.Conversation;
import dev.victormartin.oci.genai.backend.backend.data.ConversationRepository;
import dev.victormartin.oci.genai.backend.backend.data.InteractionEvent;
import dev.victormartin.oci.genai.backend.backend.data.InteractionEventRepository;
import dev.victormartin.oci.genai.backend.backend.data.MemoryLong;
import dev.victormartin.oci.genai.backend.backend.data.MemoryLongRepository;
import dev.victormartin.oci.genai.backend.backend.data.Message;
import dev.victormartin.oci.genai.backend.backend.data.MessageRepository;
import dev.victormartin.oci.genai.backend.backend.service.MemoryService;
import dev.victormartin.oci.genai.backend.backend.service.OCIGenAIService;

@Controller
public class PromptController {

    Logger logger = LoggerFactory.getLogger(PromptController.class);

    @Value("${genai.chat_model_id}")
    private String hardcodedChatModelId;

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final InteractionEventRepository interactionEventRepository;
    private final MemoryLongRepository memoryLongRepository;
    private final MemoryService memoryService;

    @Autowired
    OCIGenAIService genAI;

    public PromptController(ConversationRepository conversationRepository,
                            MessageRepository messageRepository,
                            InteractionEventRepository interactionEventRepository,
                            MemoryLongRepository memoryLongRepository,
                            MemoryService memoryService,
                            OCIGenAIService genAI) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.interactionEventRepository = interactionEventRepository;
        this.memoryLongRepository = memoryLongRepository;
        this.memoryService = memoryService;
        this.genAI = genAI;
    }

    private String buildContext(String summary, java.util.List<Message> recentAsc) {
        StringBuilder sb = new StringBuilder();
        sb.append("[Memory]\n");
        if (summary != null && !summary.isBlank()) {
            sb.append(summary.trim()).append("\n\n");
        } else {
            sb.append("(none)\n\n");
        }
        sb.append("[Recent messages]\n");
        for (Message m : recentAsc) {
            String role = m.getRole() == null ? "unknown" : m.getRole();
            String content = m.getContent() == null ? "" : m.getContent();
            if (content.length() > 1000) content = content.substring(0, 1000) + "…";
            sb.append("- ").append(role).append(": ").append(content).append("\n");
        }
        sb.append("\n");
        return sb.toString();
    }

    @MessageMapping("/prompt")
    @SendToUser("/queue/answer")
    public Answer handlePrompt(Prompt prompt) {
        String promptEscaped = HtmlUtils.htmlEscape(prompt.content());
        boolean finetune = prompt.finetune();
        String activeModel = (prompt.modelId() == null) ? hardcodedChatModelId : prompt.modelId();
        logger.info("Prompt " + promptEscaped + " received, on model " + activeModel);

        String conversationId = (prompt.conversationId() == null || prompt.conversationId().isBlank())
                ? UUID.randomUUID().toString()
                : prompt.conversationId();

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
            if (prompt.content().isEmpty()) {
                throw new InvalidPromptRequest();
            }

            // user message
            Message mUser = new Message(UUID.randomUUID().toString(), conversationId, "user", promptEscaped);
            messageRepository.save(mUser);

            // build conversational context
            List<Message> recentDesc = messageRepository.findTop20ByConversationIdOrderByCreatedAtDesc(conversationId);
            List<Message> recentAsc = new ArrayList<>();
            if (recentDesc != null && !recentDesc.isEmpty()) {
                for (int i = recentDesc.size() - 1; i >= 0; i--) {
                    recentAsc.add(recentDesc.get(i));
                }
            }
            String summary = null;
            try {
                summary = memoryLongRepository.findById(conversationId)
                        .map(MemoryLong::getSummaryText)
                        .orElse(null);
            } catch (Exception ignore) {}
            String context = buildContext(summary, recentAsc);
            String modelInput = context + "[User]\n" + promptEscaped;

            // call model (capture usage if available)
            OCIGenAIService.ModelResponse modelResp = genAI.resolvePromptWithUsage(modelInput, activeModel, finetune, false);
            String responseFromGenAI = modelResp.getContent();

            // assistant message
            Message mAsst = new Message(UUID.randomUUID().toString(), conversationId, "assistant", responseFromGenAI);
            messageRepository.save(mAsst);
            // update rolling memory
            memoryService.updateRollingSummary(conversationId);

            // telemetry
            long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
            InteractionEvent ev = new InteractionEvent("default", "chat", activeModel);
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

            return new Answer(responseFromGenAI, "");

        } catch (BmcException exception) {
            logger.error("Message: {}", exception.getMessage());
            logger.error("Original Message: {}", exception.getOriginalMessage());
            logger.error("Unmodified Message: {}", exception.getUnmodifiedMessage());
            logger.error("Service Details: {}", exception.getServiceDetails());
            logger.error("Status Code: {}", exception.getStatusCode());
            String unmodifiedMessage = exception.getUnmodifiedMessage();
            int statusCode = exception.getStatusCode();
            String errorMessage = statusCode + " " + unmodifiedMessage;
            logger.error(errorMessage);

            // telemetry on error
            try {
                long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
                InteractionEvent ev = new InteractionEvent("default", "chat", activeModel);
                ev.setLatencyMs(latencyMs);
                interactionEventRepository.save(ev);
            } catch (Exception ignore) {}

            return new Answer("", errorMessage);
        } catch (InvalidPromptRequest exception) {
            int statusCode = HttpStatus.BAD_REQUEST.value();
            String errorMessage = statusCode + " Invalid Prompt ";
            logger.error(errorMessage);

            try {
                long latencyMs = (System.nanoTime() - t0) / 1_000_000L;
                InteractionEvent ev = new InteractionEvent("default", "chat", activeModel);
                ev.setLatencyMs(latencyMs);
                interactionEventRepository.save(ev);
            } catch (Exception ignore) {}

            return new Answer("", errorMessage);
        }
    }

}
