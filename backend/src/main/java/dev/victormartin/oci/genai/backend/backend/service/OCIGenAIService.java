package dev.victormartin.oci.genai.backend.backend.service;

import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class OCIGenAIService {

        Logger log = LoggerFactory.getLogger(OCIGenAIService.class);

        @Value("${genai.compartment_id}")
        private String COMPARTMENT_ID;

        @Value("${genai.dedicated_endpoint_id}")
        private String DEDICATED_ENDPOINT_ID;

        @Autowired
        private GenAiInferenceClientService generativeAiInferenceClientService;

        @Autowired
        private GenAIModelsService genAIModelsService;

        @Autowired
        private InferenceCohereService inferenceCohere;

        @Autowired
        private InferenceMetaService inferenceMeta;

        public String resolvePrompt(String input, String modelId, boolean finetune, boolean summarization) {

                List<GenAiModel> models = genAIModelsService.getModels();
                GenAiModel currentModel = models.stream()
                        .filter(m-> modelId.equals(m.id()))
                        .findFirst()
                        .orElse(null);


                if (currentModel != null && currentModel.vendor().equals("cohere")) {
                        if (finetune) {
                                String inferedText = inferenceCohere.infereByCustomModel(input, summarization);
                                return inferedText;
                        } else {
                                String inferedText = inferenceCohere.infereByOnDemand(input, currentModel.id(), summarization);
                                return inferedText;
                        }
                } else {
                        if (finetune) {
                                String inferedText = inferenceMeta.infereByCustomModel(input, summarization);
                                return inferedText;
                        } else {
                                String inferedText = inferenceMeta.infereByOnDemand(input, modelId, summarization);
                                return inferedText;
                        }
                }
        }

        public String summaryText(String input, String modelId, boolean finetuned) {
                String response = resolvePrompt(input, modelId, finetuned, true);
                return response;
        }
}
