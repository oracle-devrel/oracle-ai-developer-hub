package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import dev.victormartin.oci.genai.backend.backend.data.MemoryLong;
import dev.victormartin.oci.genai.backend.backend.data.MemoryLongRepository;
import dev.victormartin.oci.genai.backend.backend.service.MemoryService;

@RestController
public class MemoryController {

  private static final Logger log = LoggerFactory.getLogger(MemoryController.class);

  private final MemoryService memoryService;
  private final MemoryLongRepository memoryLongRepository;

  public MemoryController(MemoryService memoryService, MemoryLongRepository memoryLongRepository) {
    this.memoryService = memoryService;
    this.memoryLongRepository = memoryLongRepository;
  }

  // -------- memory_kv --------

  @PostMapping(value = "/api/memory/kv/{conversationId}/{key}", consumes = MediaType.APPLICATION_JSON_VALUE)
  public ResponseEntity<Void> upsertKv(@PathVariable("conversationId") String conversationId,
                                       @PathVariable("key") String key,
                                       @RequestParam(value = "ttlSeconds", required = false) Long ttlSeconds,
                                       @RequestBody String valueJson) {
    memoryService.setKv(conversationId, key, valueJson, ttlSeconds);
    return ResponseEntity.noContent().build();
  }

  @GetMapping(value = "/api/memory/kv/{conversationId}/{key}", produces = MediaType.APPLICATION_JSON_VALUE)
  public ResponseEntity<String> getKv(@PathVariable("conversationId") String conversationId,
                                      @PathVariable("key") String key) {
    Optional<String> val = memoryService.getKv(conversationId, key);
    return val.map(v -> ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(v))
              .orElseGet(() -> ResponseEntity.notFound().build());
  }

  @DeleteMapping("/api/memory/kv/{conversationId}/{key}")
  public ResponseEntity<Void> deleteKv(@PathVariable("conversationId") String conversationId,
                                       @PathVariable("key") String key) {
    memoryService.deleteKv(conversationId, key);
    return ResponseEntity.noContent().build();
  }

  // -------- memory_long --------

  @GetMapping(value = "/api/memory/long/{conversationId}", produces = MediaType.TEXT_PLAIN_VALUE)
  public ResponseEntity<String> getRollingSummary(@PathVariable("conversationId") String conversationId) {
    Optional<MemoryLong> ml = memoryLongRepository.findById(conversationId);
    if (ml.isPresent() && ml.get().getSummaryText() != null) {
      return ResponseEntity.ok(ml.get().getSummaryText());
    }
    return ResponseEntity.notFound().build();
  }
}
