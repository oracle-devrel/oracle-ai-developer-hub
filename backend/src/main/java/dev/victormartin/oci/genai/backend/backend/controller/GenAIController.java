package dev.victormartin.oci.genai.backend.backend.controller;

import java.util.List;
import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.oracle.bmc.generativeai.GenerativeAiClient;
import com.oracle.bmc.generativeai.requests.ListEndpointsRequest;
import com.oracle.bmc.generativeai.responses.ListEndpointsResponse;

import dev.victormartin.oci.genai.backend.backend.dao.GenAiEndpoint;
import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;
import dev.victormartin.oci.genai.backend.backend.dto.RagQuestionDto;
import dev.victormartin.oci.genai.backend.backend.service.GenAIModelsService;
import dev.victormartin.oci.genai.backend.backend.service.GenAiClientService;
import dev.victormartin.oci.genai.backend.backend.service.RagService;

@RestController
public class GenAIController {
    Logger logger = LoggerFactory.getLogger(GenAIController.class);

    @Value("${genai.compartment_id}")
    private String COMPARTMENT_ID;

    @Autowired
    private GenAiClientService generativeAiClientService;

    @Autowired
    private GenAIModelsService genAIModelsService;

    @Autowired
    private RagService ragService;

    @GetMapping("/api/genai/models")
    public List<GenAiModel> getModels() {
        logger.info("getModels()");
        List<GenAiModel> models = genAIModelsService.getModels();
        return models.stream()
                .filter(m -> m.capabilities().contains("CHAT"))
                .filter(m -> m.vendor().equals("cohere") || m.vendor().equals("meta") || m.vendor().equals("xai"))
                .collect(Collectors.toList());
    }

    @GetMapping("/api/genai/endpoints")
    public List<GenAiEndpoint> getEndpoints() {
        logger.info("getEndpoints()");
        ListEndpointsRequest listEndpointsRequest = ListEndpointsRequest.builder().compartmentId(COMPARTMENT_ID)
                .build();
        GenerativeAiClient client = generativeAiClientService.getClient();
        ListEndpointsResponse response = client.listEndpoints(listEndpointsRequest);
        return response.getEndpointCollection().getItems().stream().map(e -> {
            GenAiEndpoint endpoint = new GenAiEndpoint(e.getId(), e.getDisplayName(), e.getLifecycleState(),
                    e.getModelId(), e.getTimeCreated());
            return endpoint;
        }).collect(Collectors.toList());
    }

    @PostMapping("/api/genai/rag")
    public String askWithRag(@RequestBody RagQuestionDto ragQuestion) {
        logger.info("askWithRag(): {}", ragQuestion.question());
        return ragService.answerWithRag(ragQuestion);
    }
}
