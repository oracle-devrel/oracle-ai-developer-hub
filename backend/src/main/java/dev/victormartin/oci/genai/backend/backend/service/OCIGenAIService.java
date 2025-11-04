package dev.victormartin.oci.genai.backend.backend.service;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.oracle.bmc.generativeaiinference.model.BaseChatResponse;
import com.oracle.bmc.generativeaiinference.model.ChatChoice;
import com.oracle.bmc.generativeaiinference.model.ChatContent;
import com.oracle.bmc.generativeaiinference.model.ChatDetails;
import com.oracle.bmc.generativeaiinference.model.ChatResult;
import com.oracle.bmc.generativeaiinference.model.CohereChatRequest;
import com.oracle.bmc.generativeaiinference.model.CohereChatResponse;
import com.oracle.bmc.generativeaiinference.model.GenericChatRequest;
import com.oracle.bmc.generativeaiinference.model.GenericChatResponse;
import com.oracle.bmc.generativeaiinference.model.Message;
import com.oracle.bmc.generativeaiinference.model.OnDemandServingMode;
import com.oracle.bmc.generativeaiinference.model.TextContent;
import com.oracle.bmc.generativeaiinference.model.UserMessage;
import com.oracle.bmc.generativeaiinference.requests.ChatRequest;
import com.oracle.bmc.generativeaiinference.responses.ChatResponse;

import dev.victormartin.oci.genai.backend.backend.dao.GenAiModel;

@Service
public class OCIGenAIService {

        Logger log = LoggerFactory.getLogger(OCIGenAIService.class);

        @Value("${genai.compartment_id}")
        private String COMPARTMENT_ID;

        @Autowired
        private GenAiInferenceClientService generativeAiInferenceClientService;

        @Autowired
        private GenAIModelsService genAIModelsService;

        // Model response with usage/cost information
        public static class ModelResponse {
                private final String content;
                private final Integer tokensIn;
                private final Integer tokensOut;
                private final Double cost;
                public ModelResponse(String content, Integer tokensIn, Integer tokensOut, Double cost) {
                        this.content = content;
                        this.tokensIn = tokensIn;
                        this.tokensOut = tokensOut;
                        this.cost = cost;
                }
                public String getContent() { return content; }
                public Integer getTokensIn() { return tokensIn; }
                public Integer getTokensOut() { return tokensOut; }
                public Double getCost() { return cost; }
        }

        public ModelResponse resolvePromptWithUsage(String input, String modelId, boolean finetune, boolean summarization) {

                List<GenAiModel> models = genAIModelsService.getModels();
                GenAiModel currentModel = models.stream()
                        .filter(m-> modelId.equals(m.id()))
                        .findFirst()
                        .orElseThrow();

                log.info("Model {} with finetune {}", currentModel.name(), finetune? "yes" : "no");

                double temperature = summarization?0.0:0.5;

                String inputText = summarization?"Summarize this text:\n" + input: input;

                ChatDetails chatDetails;
                switch (currentModel.vendor()) {
                        case "cohere":
                                CohereChatRequest cohereChatRequest = CohereChatRequest.builder()
                                        .message(inputText)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double) 0)
                                        .topP(0.75)
                                        .topK(0)
                                        .isStream(false) // TODO websockets and streams
                                        .build();

                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(cohereChatRequest)
                                        .build();
                                break;
                        case "meta":
                                ChatContent content = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> contents = new ArrayList<>();
                                contents.add(content);
                                List<Message> messages = new ArrayList<>();
                                Message message = new UserMessage(contents, "user");
                                messages.add(message);
                                GenericChatRequest genericChatRequest = GenericChatRequest.builder()
                                        .messages(messages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double)0)
                                        .topP(0.75)
                                        .topK(-1)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(genericChatRequest)
                                        .build();
                                break;
                        case "xai":
                                ChatContent xaiContent = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> xaiContents = new ArrayList<>();
                                xaiContents.add(xaiContent);
                                List<Message> xaiMessages = new ArrayList<>();
                                Message xaiMessage = new UserMessage(xaiContents, "user");
                                xaiMessages.add(xaiMessage);
                                GenericChatRequest xaiGenericChatRequest = GenericChatRequest.builder()
                                        .messages(xaiMessages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .topP(0.75)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(xaiGenericChatRequest)
                                        .build();
                                break;
                        default:
                                log.warn("Provider {} not explicitly supported, falling back to GenericChatRequest", currentModel.vendor());
                                ChatContent fbContent = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> fbContents = new ArrayList<>();
                                fbContents.add(fbContent);
                                List<Message> fbMessages = new ArrayList<>();
                                Message fbMessage = new UserMessage(fbContents, "user");
                                fbMessages.add(fbMessage);
                                GenericChatRequest fbGenericChatRequest = GenericChatRequest.builder()
                                        .messages(fbMessages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double)0)
                                        .topP(0.75)
                                        .topK(-1)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(fbGenericChatRequest)
                                        .build();
                                break;
                }

                ChatRequest request = ChatRequest.builder()
                        .chatDetails(chatDetails)
                        .build();
                ChatResponse response = generativeAiInferenceClientService.getClient().chat(request);
                ChatResult chatResult = response.getChatResult();

                String textOut = null;
                BaseChatResponse baseChatResponse = chatResult.getChatResponse();
                if (baseChatResponse instanceof CohereChatResponse) {
                        textOut = ((CohereChatResponse)baseChatResponse).getText();
                } else if (baseChatResponse instanceof GenericChatResponse) {
                        List<ChatChoice> choices = ((GenericChatResponse) baseChatResponse).getChoices();
                        List<ChatContent> contents2 = choices.get(choices.size() - 1).getMessage().getContent();
                        ChatContent content2 = contents2.get(contents2.size() - 1);
                        if (content2 instanceof TextContent) {
                                textOut = ((TextContent) content2).getText();
                        }
                }
                if (textOut == null) {
                        throw new IllegalStateException("Unexpected chat response type: " + baseChatResponse.getClass().getName());
                }

                Integer tokensIn = null;
                Integer tokensOut = null;
                Double cost = null;
                try {
                        Object usage = null;
                        try {
                                usage = response.getClass().getMethod("getUsage").invoke(response);
                        } catch (Exception ignore) {}
                        if (usage == null) {
                                try {
                                        usage = chatResult.getClass().getMethod("getUsage").invoke(chatResult);
                                } catch (Exception ignore) {}
                        }
                        if (usage != null) {
                                try {
                                        Object in = usage.getClass().getMethod("getInputTokenCount").invoke(usage);
                                        Object out = usage.getClass().getMethod("getOutputTokenCount").invoke(usage);
                                        if (in instanceof Number) tokensIn = ((Number) in).intValue();
                                        if (out instanceof Number) tokensOut = ((Number) out).intValue();
                                } catch (Exception ignore) {}
                        }
                        cost = calculateCost(tokensIn, tokensOut, currentModel.id());
                } catch (Exception e) {
                        log.debug("No usage info available: {}", e.getMessage());
                }

                return new ModelResponse(textOut, tokensIn, tokensOut, cost);
        }

        private Double calculateCost(Integer inTok, Integer outTok, String modelId) {
                if (inTok == null || outTok == null) return null;
                double inRatePer1k = 0.0005;  // example placeholder
                double outRatePer1k = 0.0015; // example placeholder
                return (inTok / 1000.0) * inRatePer1k + (outTok / 1000.0) * outRatePer1k;
        }

        public String resolvePrompt(String input, String modelId, boolean finetune, boolean summarization) {

                List<GenAiModel> models = genAIModelsService.getModels();
                GenAiModel currentModel = models.stream()
                        .filter(m-> modelId.equals(m.id()))
                        .findFirst()
                        .orElseThrow();

                log.info("Model {} with finetune {}", currentModel.name(), finetune? "yes" : "no");

                double temperature = summarization?0.0:0.5;

                String inputText = summarization?"Summarize this text:\n" + input: input;

                        ChatDetails chatDetails;
                switch (currentModel.vendor()) {
                        case "cohere":
                                CohereChatRequest cohereChatRequest = CohereChatRequest.builder()
                                        .message(inputText)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double) 0)
                                        .topP(0.75)
                                        .topK(0)
                                        .isStream(false) // TODO websockets and streams
                                        .build();

                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(cohereChatRequest)
                                        .build();
                                break;
                        case "meta":
                                ChatContent content = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> contents = new ArrayList<>();
                                contents.add(content);
                                List<Message> messages = new ArrayList<>();
                                Message message = new UserMessage(contents, "user");
                                messages.add(message);
                                GenericChatRequest genericChatRequest = GenericChatRequest.builder()
                                        .messages(messages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double)0)
                                        .topP(0.75)
                                        .topK(-1)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(genericChatRequest)
                                        .build();
                                break;
                        case "xai":
                                ChatContent xaiContent = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> xaiContents = new ArrayList<>();
                                xaiContents.add(xaiContent);
                                List<Message> xaiMessages = new ArrayList<>();
                                Message xaiMessage = new UserMessage(xaiContents, "user");
                                xaiMessages.add(xaiMessage);
                                GenericChatRequest xaiGenericChatRequest = GenericChatRequest.builder()
                                        .messages(xaiMessages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .topP(0.75)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(xaiGenericChatRequest)
                                        .build();
                                break;
                        default:
                                log.warn("Provider {} not explicitly supported, falling back to GenericChatRequest", currentModel.vendor());
                                ChatContent fbContent = TextContent.builder()
                                        .text(inputText)
                                        .build();
                                List<ChatContent> fbContents = new ArrayList<>();
                                fbContents.add(fbContent);
                                List<Message> fbMessages = new ArrayList<>();
                                Message fbMessage = new UserMessage(fbContents, "user");
                                fbMessages.add(fbMessage);
                                GenericChatRequest fbGenericChatRequest = GenericChatRequest.builder()
                                        .messages(fbMessages)
                                        .maxTokens(600)
                                        .temperature(temperature)
                                        .frequencyPenalty((double)0)
                                        .topP(0.75)
                                        .topK(-1)
                                        .isStream(false)
                                        .build();
                                chatDetails = ChatDetails.builder()
                                        .servingMode(OnDemandServingMode.builder().modelId(currentModel.id()).build())
                                        .compartmentId(COMPARTMENT_ID)
                                        .chatRequest(fbGenericChatRequest)
                                        .build();
                                break;
                }

                ChatRequest request = ChatRequest.builder()
                        .chatDetails(chatDetails)
                        .build();
                ChatResponse response = generativeAiInferenceClientService.getClient().chat(request);
                ChatResult chatResult = response.getChatResult();

                BaseChatResponse baseChatResponse = chatResult.getChatResponse();
                if (baseChatResponse instanceof CohereChatResponse) {
                        return ((CohereChatResponse)baseChatResponse).getText();
                } else if (baseChatResponse instanceof GenericChatResponse) {
                        List<ChatChoice> choices = ((GenericChatResponse) baseChatResponse).getChoices();
                        List<ChatContent> contents = choices.get(choices.size() - 1).getMessage().getContent();
                        ChatContent content = contents.get(contents.size() - 1);
                        if (content instanceof TextContent) {
                                return ((TextContent) content).getText();
                        }
                }
                throw new IllegalStateException("Unexpected chat response type: " + baseChatResponse.getClass().getName());
        }

        public String summaryText(String input, String modelId, boolean finetuned) {
                String response = resolvePrompt(input, modelId, finetuned, true);
                return response;
        }
}
