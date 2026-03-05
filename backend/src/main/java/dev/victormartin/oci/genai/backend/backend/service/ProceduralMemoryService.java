package dev.victormartin.oci.genai.backend.backend.service;

import org.springframework.stereotype.Service;

/**
 * Thin helper around MemoryService to persist procedural/workflow memory.
 * Stores workflow state in memory_kv using stable keys.
 */
@Service
public class ProceduralMemoryService {

  private final MemoryService memoryService;

  public ProceduralMemoryService(MemoryService memoryService) {
    this.memoryService = memoryService;
  }

  public void markRagStarted(String conversationId, String question) {
    String escapedQuestion = escape(question);
    memoryService.setKv(conversationId, "workflow.step", "{\"value\":\"rag.retrieve\"}", 3600L);
    memoryService.setKv(conversationId, "workflow.status", "{\"value\":\"running\"}", 3600L);
    memoryService.setKv(
        conversationId,
        "workflow.plan",
        "{\"value\":[\"retrieve_context\",\"ground_response\",\"persist_memory\"]}",
        3600L);
    memoryService.setKv(
        conversationId,
        "workflow.lastInput",
        "{\"question\":\"" + escapedQuestion + "\"}",
        3600L);
  }

  public void markRagCompleted(String conversationId) {
    memoryService.setKv(conversationId, "workflow.step", "{\"value\":\"rag.complete\"}", 3600L);
    memoryService.setKv(conversationId, "workflow.status", "{\"value\":\"completed\"}", 3600L);
  }

  public void markRagFailed(String conversationId, String error) {
    String escapedError = escape(error);
    memoryService.setKv(conversationId, "workflow.step", "{\"value\":\"rag.error\"}", 3600L);
    memoryService.setKv(conversationId, "workflow.status", "{\"value\":\"failed\"}", 3600L);
    memoryService.setKv(
        conversationId,
        "workflow.lastError",
        "{\"message\":\"" + escapedError + "\"}",
        1800L);
  }

  private String escape(String s) {
    if (s == null) return "";
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
  }
}