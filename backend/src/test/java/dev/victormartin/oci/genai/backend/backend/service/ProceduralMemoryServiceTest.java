package dev.victormartin.oci.genai.backend.backend.service;

import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import org.junit.jupiter.api.Test;

class ProceduralMemoryServiceTest {

  @Test
  void markRagStarted_persistsExpectedWorkflowKeys() {
    MemoryService memoryService = mock(MemoryService.class);
    ProceduralMemoryService proceduralMemoryService = new ProceduralMemoryService(memoryService);

    proceduralMemoryService.markRagStarted("conv-1", "How are you?");

    verify(memoryService, times(1)).setKv(eq("conv-1"), eq("workflow.step"), eq("{\"value\":\"rag.retrieve\"}"), anyLong());
    verify(memoryService, times(1)).setKv(eq("conv-1"), eq("workflow.status"), eq("{\"value\":\"running\"}"), anyLong());
    verify(memoryService, times(1)).setKv(eq("conv-1"), eq("workflow.plan"), eq("{\"value\":[\"retrieve_context\",\"ground_response\",\"persist_memory\"]}"), anyLong());
    verify(memoryService, times(1)).setKv(eq("conv-1"), eq("workflow.lastInput"), eq("{\"question\":\"How are you?\"}"), anyLong());
  }

  @Test
  void markRagFailed_persistsFailureStatus() {
    MemoryService memoryService = mock(MemoryService.class);
    ProceduralMemoryService proceduralMemoryService = new ProceduralMemoryService(memoryService);

    proceduralMemoryService.markRagFailed("conv-2", "boom");

    verify(memoryService, times(1)).setKv(eq("conv-2"), eq("workflow.step"), eq("{\"value\":\"rag.error\"}"), anyLong());
    verify(memoryService, times(1)).setKv(eq("conv-2"), eq("workflow.status"), eq("{\"value\":\"failed\"}"), anyLong());
    verify(memoryService, times(1)).setKv(eq("conv-2"), eq("workflow.lastError"), eq("{\"message\":\"boom\"}"), anyLong());
  }
}
