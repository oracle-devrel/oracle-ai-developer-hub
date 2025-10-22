package dev.victormartin.oci.genai.backend.backend.service;

import dev.victormartin.oci.genai.backend.backend.data.MemoryKv;
import dev.victormartin.oci.genai.backend.backend.data.MemoryKvId;
import dev.victormartin.oci.genai.backend.backend.data.MemoryKvRepository;
import dev.victormartin.oci.genai.backend.backend.data.MemoryLong;
import dev.victormartin.oci.genai.backend.backend.data.MemoryLongRepository;
import dev.victormartin.oci.genai.backend.backend.data.Message;
import dev.victormartin.oci.genai.backend.backend.data.MessageRepository;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class MemoryService {

  private static final Logger log = LoggerFactory.getLogger(MemoryService.class);

  private final MessageRepository messageRepository;
  private final MemoryLongRepository memoryLongRepository;
  private final MemoryKvRepository memoryKvRepository;
  private final OCIGenAIService ociGenAIService;
  private final Environment env;

  // Tunables
  private static final int MAX_MESSAGES_PER_UPDATE = 20;

  public MemoryService(
      MessageRepository messageRepository,
      MemoryLongRepository memoryLongRepository,
      MemoryKvRepository memoryKvRepository,
      OCIGenAIService ociGenAIService,
      Environment env) {
    this.messageRepository = messageRepository;
    this.memoryLongRepository = memoryLongRepository;
    this.memoryKvRepository = memoryKvRepository;
    this.ociGenAIService = ociGenAIService;
    this.env = env;
  }

  /**
   * Refresh the rolling summary for a conversation using new messages since the last update.
   * Best-effort; logs and returns on failure so it never blocks chat.
   */
  @Transactional
  public void updateRollingSummary(String conversationId) {
    try {
      Optional<MemoryLong> current = memoryLongRepository.findById(conversationId);
      String previousSummary = current.map(MemoryLong::getSummaryText).orElse(null);
      OffsetDateTime since =
          current.map(MemoryLong::getUpdatedAt).orElse(OffsetDateTime.parse("1970-01-01T00:00:00Z"));

      List<Message> newMessages = new ArrayList<>();
      // Prefer bounded window to avoid huge prompts
      List<Message> recent = messageRepository.findTop20ByConversationIdOrderByCreatedAtDesc(conversationId);
      if (recent != null && !recent.isEmpty()) {
        // reverse to ascending by createdAt
        for (int i = recent.size() - 1; i >= 0; i--) {
          Message m = recent.get(i);
          if (m.getCreatedAt() == null || m.getCreatedAt().isAfter(since)) {
            newMessages.add(m);
          }
        }
      }

      if (newMessages.isEmpty()) {
        return; // nothing new to summarize
      }

      // Build summarization prompt
      String prompt = buildSummaryPrompt(previousSummary, newMessages);

      // Choose summarization model (fallback to chat model if not configured)
      String modelId = env.getProperty("genai.summarization_model_id",
          env.getProperty("genai.chat_model_id"));

      String newSummary = ociGenAIService.summaryText(prompt, modelId, false);

      MemoryLong ml = new MemoryLong(conversationId, newSummary);
      memoryLongRepository.save(ml);
      log.info("memory_long updated for conversation={} ({} chars)", conversationId, newSummary.length());

    } catch (Exception e) {
      log.warn("Rolling summary update failed for conversation {}: {}", conversationId, e.getMessage());
    }
  }

  private String buildSummaryPrompt(String previousSummary, List<Message> newMessages) {
    StringBuilder sb = new StringBuilder();
    sb.append("SYSTEM:\nYou are a concise summarizer that maintains long-term memory for a conversation.\n")
      .append("Summarize NEW_MESSAGES in 5-8 bullet points, preserving entities, tasks, preferences, and any decisions.\n")
      .append("If PREVIOUS_SUMMARY exists, update/merge it; do not duplicate. Return only the updated summary text.\n\n");
    if (previousSummary != null && !previousSummary.isBlank()) {
      sb.append("PREVIOUS_SUMMARY:\n").append(previousSummary).append("\n\n");
    } else {
      sb.append("PREVIOUS_SUMMARY:\n(none)\n\n");
    }
    sb.append("NEW_MESSAGES:\n");
    int count = 0;
    for (Message m : newMessages) {
      if (count >= MAX_MESSAGES_PER_UPDATE) break;
      String role = m.getRole() == null ? "unknown" : m.getRole();
      String content = m.getContent() == null ? "" : m.getContent();
      sb.append("- ").append(role).append(": ").append(content).append("\n");
      count++;
    }
    sb.append("\nOUTPUT:\n");
    return sb.toString();
  }

  // ===================== KV Store =====================

  @Transactional
  public void setKv(String conversationId, String key, String valueJson, Long ttlSeconds) {
    OffsetDateTime ttlTs = null;
    if (ttlSeconds != null && ttlSeconds > 0) {
      ttlTs = OffsetDateTime.now().plusSeconds(ttlSeconds);
    }
    MemoryKv kv = new MemoryKv(conversationId, key, valueJson, ttlTs);
    memoryKvRepository.save(kv);
  }

  @Transactional(readOnly = true)
  public Optional<String> getKv(String conversationId, String key) {
    Optional<MemoryKv> kvOpt = memoryKvRepository.findByConversationIdAndKey(conversationId, key);
    if (kvOpt.isEmpty()) return Optional.empty();
    MemoryKv kv = kvOpt.get();
    if (kv.getTtlTs() != null && kv.getTtlTs().isBefore(OffsetDateTime.now())) {
      return Optional.empty();
    }
    return Optional.ofNullable(kv.getValueJson());
  }

  @Transactional
  public void deleteKv(String conversationId, String key) {
    memoryKvRepository.deleteById(new MemoryKvId(conversationId, key));
  }

  @Scheduled(fixedDelay = 900_000L) // every 15 minutes
  @Transactional
  public void cleanupExpiredKv() {
    try {
      int removed = memoryKvRepository.deleteByTtlTsBefore(OffsetDateTime.now());
      if (removed > 0) {
        log.info("memory_kv cleanup removed {} expired entries", removed);
      }
    } catch (Exception e) {
      log.warn("memory_kv cleanup failed: {}", e.getMessage());
    }
  }
}
