package dev.victormartin.oci.genai.backend.backend.service;

import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.ChatRequest;
import com.oracle.bmc.generativeaiinference.responses.ChatResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class InferenceCohereService {

    Logger log = LoggerFactory.getLogger(InferenceCohereService.class);

    @Value("${genai.compartment_id}")
    private String COMPARTMENT_ID;

    @Value("${genai.dedicated_endpoint_id}")
    private String DEDICATED_ENDPOINT_ID;

    @Autowired
    private GenAiInferenceClientService generativeAiInferenceClientService;

    public String infereByCustomModel(String input, boolean summarization) {
        double temperature = summarization?0.0:0.5;
        String inputText = summarization?"Summarize this text:\n" + input: input;

        ServingMode dedicatedServingMode = DedicatedServingMode.builder()
                .endpointId(DEDICATED_ENDPOINT_ID)
                .build();
        GenericChatRequest genericChatRequest = getGenericChatRequest(inputText, temperature);
        ChatDetails chatDetails = ChatDetails.builder()
                .servingMode(dedicatedServingMode)
                .compartmentId(COMPARTMENT_ID)
                .chatRequest(genericChatRequest)
                .build();

        ChatRequest request = ChatRequest.builder()
                .chatDetails(chatDetails)
                .build();
        ChatResponse response = generativeAiInferenceClientService.getClient().chat(request);
        ChatResult chatResult = response.getChatResult();
        BaseChatResponse baseChatResponse = chatResult.getChatResponse();
        List<ChatChoice> choices = ((GenericChatResponse) baseChatResponse).getChoices();
        List<ChatContent> contents = choices.get(choices.size() - 1).getMessage().getContent();
        ChatContent content = contents.get(contents.size() - 1);
        if (content instanceof TextContent) {
            return ((TextContent) content).getText();
        }
        return "";
    }
    public String infereByOnDemand(String input, String modelId, boolean summarization) {
        double temperature = summarization?0.0:0.5;
        String inputText = summarization?"Summarize this text:\n" + input: input;

        ServingMode onDemandServingMode = OnDemandServingMode.builder()
                .modelId(modelId)
                .build();
        CohereChatRequest cohereChatRequest = CohereChatRequest.builder()
                .message(inputText)
                .maxTokens(600)
                .temperature(temperature)
                .frequencyPenalty((double) 0)
                .topP(0.75)
                .topK(0)
                .isStream(false) // TODO websockets and streams
                .build();

        ChatDetails chatDetails = ChatDetails.builder()
                .servingMode(onDemandServingMode)
                .compartmentId(COMPARTMENT_ID)
                .chatRequest(cohereChatRequest)
                .build();
        ChatRequest request = ChatRequest.builder()
                .chatDetails(chatDetails)
                .build();
        ChatResponse response = generativeAiInferenceClientService.getClient().chat(request);
        ChatResult chatResult = response.getChatResult();

        BaseChatResponse baseChatResponse = chatResult.getChatResponse();
        return ((CohereChatResponse)baseChatResponse).getText();
    }

    GenericChatRequest getGenericChatRequest(String input, double temperature) {
        ChatContent content = TextContent.builder()
                .text(input)
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
                .frequencyPenalty((double) 0)
                .presencePenalty((double) 0)
                .topP(0.75)
                .topK(-1)
                .isStream(false)
                .build();
        return genericChatRequest;
    }
}
