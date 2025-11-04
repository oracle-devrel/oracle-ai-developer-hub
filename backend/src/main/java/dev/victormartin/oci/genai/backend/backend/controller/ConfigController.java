package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Small configuration endpoint to expose the default chat model id to the UI.
 */
@RestController
public class ConfigController {

  @Value("${genai.chat_model_id}")
  private String chatModelId;

  @GetMapping("/api/genai/default-model")
  public Map<String, String> getDefaultModel() {
    // Response shape: { "modelId": "..." }
    return Map.of("modelId", chatModelId);
  }
}
