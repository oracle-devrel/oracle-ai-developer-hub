Generative AI Service Inference API
​/20231130
OCI Generative AI is a fully managed service that provides a set of state-of-the-art, customizable large language models (LLMs) that cover a wide range of use cases for text generation, summarization, and text embeddings.

Use the Generative AI service inference API to access your custom model endpoints, or to try the out-of-the-box models to chat, generate text, summarize, and create text embeddings.

To use a Generative AI custom model for inference, you must first create an endpoint for that model. Use the Generative AI service management API to create a custom model by fine-tuning an out-of-the-box model, or a previous version of a custom model, using your own data. Fine-tune the custom model on a fine-tuning dedicated AI cluster. Then, create a hosting dedicated AI cluster with an endpoint to host your custom model. For resource management in the Generative AI service, use the Generative AI service management API.

To learn more about the service, see the Generative AI documentation.

Use the table of contents and search tool to explore the Generative AI Service Inference API.

API Endpoints:

https://inference.generativeai.ap-hyderabad-1.oci.oraclecloud.com
https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com
https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com
https://inference.generativeai.me-dubai-1.oci.oraclecloud.com
https://inference.generativeai.me-riyadh-1.oci.oraclecloud.com
https://inference.generativeai.sa-saopaulo-1.oci.oraclecloud.com
https://inference.generativeai.uk-london-1.oci.oraclecloud.com
https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com
https://inference.generativeai.us-chicago-1.oci.oraclecloud.com
https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com

ChatResult Reference
The response to the chat conversation.

Attributes
chatResponse
Required: yes
Type: BaseChatResponse
modelId
Required: yes
Type: string
Min Length: 1
Max Length: 255
The OCID of the model that's used in this inference request.

modelVersion
Required: yes
Type: string
Min Length: 1
Max Length: 255
The version of the model.

Chat GenerativeAiInference
​post /20231130/actions/chat
Creates a response for the given conversation.


Request
Chat
Parameters
Name	Where	Description
opc-retry-token	
header

Required: no
Type: string
Min Length: 1
Max Length: 64
A token that uniquely identifies a request so it can be retried in case of a timeout or server error without risk of executing that same action again. Retry tokens expire after 24 hours, but can be invalidated before that, in case of conflicting operations. For example, if a resource is deleted and purged from the system, then a retry of the original creation request is rejected.

opc-request-id	
header

Required: no
Type: string
The client request ID for tracing.

Body
The request body must contain a single ChatDetails resource.

/** This is an automatically generated code sample. 
To make this code sample work in your Oracle Cloud tenancy, 
please replace the values for any parameters whose current values do not fit
your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and 
boolean, number, and enum parameters with values not fitting your use case).
*/

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.*;
import com.oracle.bmc.generativeaiinference.responses.*;
import java.math.BigDecimal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Date;
import java.util.UUID;
import java.util.Arrays;

```java
public class ChatExample {
    public static void main(String[] args) throws Exception {

        /**
         * Create a default authentication provider that uses the DEFAULT
         * profile in the configuration file.
         * Refer to <see href="https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File>the public documentation</see> on how to prepare a configuration file.
         */
        final ConfigFileReader.ConfigFile configFile = ConfigFileReader.parseDefault();
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        /* Create a service client */
        GenerativeAiInferenceClient client = GenerativeAiInferenceClient.builder().build(provider);

        /* Create a request and dependent object(s). */
	ChatDetails chatDetails = ChatDetails.builder()
		.compartmentId("ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value")
		.servingMode(DedicatedServingMode.builder()
			.endpointId("ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value").build())
		.chatRequest(GenericChatRequest.builder()
			.messages(new ArrayList<>(Arrays.asList(AssistantMessage.builder()
					.name("EXAMPLE-name-Value")
					.refusal("EXAMPLE-refusal-Value")
					.toolCalls(new ArrayList<>(Arrays.asList(FunctionCall.builder()
							.name("EXAMPLE-name-Value")
							.arguments("EXAMPLE-arguments-Value")
							.id("ocid1.test.oc1..<unique_ID>EXAMPLE-id-Value").build())))
					.annotations(new ArrayList<>(Arrays.asList(Annotation.builder()
							.type("EXAMPLE-type-Value")
							.urlCitation(UrlCitation.builder()
								.startIndex(249)
								.endIndex(175)
								.title("EXAMPLE-title-Value")
								.url("EXAMPLE-url-Value").build()).build())))
					.content(new ArrayList<>(Arrays.asList(VideoContent.builder()
							.videoUrl(VideoUrl.builder()
								.url("EXAMPLE-url-Value")
								.detail(VideoUrl.Detail.Low).build()).build()))).build())))
			.reasoningEffort(GenericChatRequest.ReasoningEffort.Low)
			.verbosity(GenericChatRequest.Verbosity.Low)
			.metadata("EXAMPLE-metadata-Value")
			.isStream(true)
			.streamOptions(StreamOptions.builder()
				.isIncludeUsage(false).build())
			.numGenerations(1)
			.seed(467)
			.isEcho(false)
			.topK(0)
			.topP(0.52461445)
			.temperature(1.6857262)
			.frequencyPenalty(1.5041656)
			.presencePenalty(1.6071491)
			.stop(new ArrayList<>(Arrays.asList("EXAMPLE--Value")))
			.logProbs(592)
			.maxTokens(661)
			.maxCompletionTokens(125)
			.logitBias("EXAMPLE-logitBias-Value")
			.prediction(StaticContent.builder()
				.content(new ArrayList<>(Arrays.asList(TextContent.builder()
						.text("EXAMPLE-text-Value").build()))).build())
			.responseFormat(JsonObjectResponseFormat.builder().build())
			.toolChoice(ToolChoiceFunction.builder()
				.name("EXAMPLE-name-Value").build())
			.isParallelToolCalls(true)
			.tools(new ArrayList<>(Arrays.asList(FunctionDefinition.builder()
					.name("EXAMPLE-name-Value")
					.description("EXAMPLE-description-Value")
					.parameters("EXAMPLE-parameters-Value").build())))
			.webSearchOptions(WebSearchOptions.builder()
				.searchContextSize(WebSearchOptions.SearchContextSize.Medium)
				.userLocation(ApproximateLocation.builder()
					.city("EXAMPLE-city-Value")
					.region("EXAMPLE-region-Value")
					.country("P8")
					.timezone("EXAMPLE-timezone-Value").build()).build()).build()).build();

	ChatRequest chatRequest = ChatRequest.builder()
		.chatDetails(chatDetails)
		.opcRetryToken("EXAMPLE-opcRetryToken-Value")
		.opcRequestId("9CA4Z7RFAJ8RJGUQISTI<unique_ID>").build();

        /* Send request to the Client */
        ChatResponse response = client.chat(chatRequest);
    }

    
}
```

```python
# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci

# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


# Initialize service client with default config file
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config)


# Send the request to service, some parameters are not required, see API
# doc for more info
chat_response = generative_ai_inference_client.chat(
    chat_details=oci.generative_ai_inference.models.ChatDetails(
        compartment_id="ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value",
        serving_mode=oci.generative_ai_inference.models.DedicatedServingMode(
            serving_type="DEDICATED",
            endpoint_id="ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value"),
        chat_request=oci.generative_ai_inference.models.GenericChatRequest(
            api_format="GENERIC",
            messages=[
                oci.generative_ai_inference.models.AssistantMessage(
                    role="ASSISTANT",
                    content=[
                        oci.generative_ai_inference.models.VideoContent(
                            type="VIDEO",
                            video_url=oci.generative_ai_inference.models.VideoUrl(
                                url="EXAMPLE-url-Value",
                                detail="LOW"))],
                    name="EXAMPLE-name-Value",
                    refusal="EXAMPLE-refusal-Value",
                    tool_calls=[
                            oci.generative_ai_inference.models.FunctionCall(
                                type="FUNCTION",
                                id="ocid1.test.oc1..<unique_ID>EXAMPLE-id-Value",
                                name="EXAMPLE-name-Value",
                                arguments="EXAMPLE-arguments-Value")],
                    annotations=[
                            oci.generative_ai_inference.models.Annotation(
                                type="EXAMPLE-type-Value",
                                url_citation=oci.generative_ai_inference.models.UrlCitation(
                                    start_index=249,
                                    end_index=175,
                                    title="EXAMPLE-title-Value",
                                    url="EXAMPLE-url-Value"))])],
            reasoning_effort="LOW",
            verbosity="LOW",
            metadata="EXAMPLE-metadata-Value",
            is_stream=True,
            stream_options=oci.generative_ai_inference.models.StreamOptions(
                is_include_usage=False),
            num_generations=1,
            seed=467,
            is_echo=False,
            top_k=0,
            top_p=0.52461445,
            temperature=1.6857262,
            frequency_penalty=1.5041656,
            presence_penalty=1.6071491,
            stop=["EXAMPLE--Value"],
            log_probs=592,
            max_tokens=661,
            max_completion_tokens=125,
            logit_bias="EXAMPLE-logitBias-Value",
            prediction=oci.generative_ai_inference.models.StaticContent(
                type="CONTENT",
                content=[
                    oci.generative_ai_inference.models.TextContent(
                        type="TEXT",
                        text="EXAMPLE-text-Value")]),
            response_format=oci.generative_ai_inference.models.JsonObjectResponseFormat(
                type="JSON_OBJECT"),
            tool_choice=oci.generative_ai_inference.models.ToolChoiceFunction(
                type="FUNCTION",
                name="EXAMPLE-name-Value"),
            is_parallel_tool_calls=True,
            tools=[
                oci.generative_ai_inference.models.FunctionDefinition(
                    type="FUNCTION",
                    name="EXAMPLE-name-Value",
                    description="EXAMPLE-description-Value",
                    parameters="EXAMPLE-parameters-Value")],
            web_search_options=oci.generative_ai_inference.models.WebSearchOptions(
                search_context_size="MEDIUM",
                user_location=oci.generative_ai_inference.models.ApproximateLocation(
                    city="EXAMPLE-city-Value",
                    region="EXAMPLE-region-Value",
                    country="P8",
                    timezone="EXAMPLE-timezone-Value")))),
    opc_retry_token="EXAMPLE-opcRetryToken-Value",
    opc_request_id="9CA4Z7RFAJ8RJGUQISTI<unique_ID>")

# Get the data from response
print(chat_response.data)
```

EmbedTextResult Reference
The generated embedded result to return.

Attributes
embeddings
Required: yes
Type: [array, ...]
The embeddings corresponding to inputs.

id
Required: yes
Type: string
A unique identifier for the generated result.

inputs
Required: no
Type: [string, ...]
The original inputs. Only present if "isEcho" is set to true.

modelId
Required: no
Type: string
The OCID of the model used in this inference request.

modelVersion
Required: no
Type: string
The version of the model.

usage
Required: no
Type: Usage

```java
/** This is an automatically generated code sample. 
To make this code sample work in your Oracle Cloud tenancy, 
please replace the values for any parameters whose current values do not fit
your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and 
boolean, number, and enum parameters with values not fitting your use case).
*/

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.*;
import com.oracle.bmc.generativeaiinference.responses.*;
import java.math.BigDecimal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Date;
import java.util.UUID;
import java.util.Arrays;


public class EmbedTextExample {
    public static void main(String[] args) throws Exception {

        /**
         * Create a default authentication provider that uses the DEFAULT
         * profile in the configuration file.
         * Refer to <see href="https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File>the public documentation</see> on how to prepare a configuration file.
         */
        final ConfigFileReader.ConfigFile configFile = ConfigFileReader.parseDefault();
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        /* Create a service client */
        GenerativeAiInferenceClient client = GenerativeAiInferenceClient.builder().build(provider);

        /* Create a request and dependent object(s). */
	EmbedTextDetails embedTextDetails = EmbedTextDetails.builder()
		.inputs(new ArrayList<>(Arrays.asList("EXAMPLE--Value")))
		.servingMode(DedicatedServingMode.builder()
			.endpointId("ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value").build())
		.compartmentId("ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value")
		.isEcho(true)
		.truncate(EmbedTextDetails.Truncate.Start)
		.inputType(EmbedTextDetails.InputType.Image).build();

	EmbedTextRequest embedTextRequest = EmbedTextRequest.builder()
		.embedTextDetails(embedTextDetails)
		.opcRetryToken("EXAMPLE-opcRetryToken-Value")
		.opcRequestId("K9W502WXV0TFNBLFZYCW<unique_ID>").build();

        /* Send request to the Client */
        EmbedTextResponse response = client.embedText(embedTextRequest);
    }

    
}
```

```python
# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci

# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


# Initialize service client with default config file
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config)


# Send the request to service, some parameters are not required, see API
# doc for more info
embed_text_response = generative_ai_inference_client.embed_text(
    embed_text_details=oci.generative_ai_inference.models.EmbedTextDetails(
        inputs=["EXAMPLE--Value"],
        serving_mode=oci.generative_ai_inference.models.DedicatedServingMode(
            serving_type="DEDICATED",
            endpoint_id="ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value"),
        compartment_id="ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value",
        is_echo=True,
        truncate="START",
        input_type="IMAGE"),
    opc_retry_token="EXAMPLE-opcRetryToken-Value",
    opc_request_id="K9W502WXV0TFNBLFZYCW<unique_ID>")

# Get the data from response
print(embed_text_response.data)
```

GenerateTextResult Reference
The generated text result to return.

Attributes
inferenceResponse
Required: yes
Type: LlmInferenceResponse
modelId
Required: yes
Type: string
Min Length: 1
Max Length: 255
The OCID of the model used in this inference request.

modelVersion
Required: yes
Type: string
Min Length: 1
Max Length: 255
The version of the model.

GenerateText GenerativeAiInference
​post /20231130/actions/generateText
Generates a text response based on the user prompt.


Request
GenerateText
Parameters
Name	Where	Description
opc-retry-token	
header

Required: no
Type: string
Min Length: 1
Max Length: 64
A token that uniquely identifies a request so it can be retried in case of a timeout or server error without risk of executing that same action again. Retry tokens expire after 24 hours, but can be invalidated before that, in case of conflicting operations. For example, if a resource is deleted and purged from the system, then a retry of the original creation request is rejected.

opc-request-id	
header

Required: no
Type: string
The client request ID for tracing.

Body
The request body must contain a single GenerateTextDetails resource.
```java
/** This is an automatically generated code sample. 
To make this code sample work in your Oracle Cloud tenancy, 
please replace the values for any parameters whose current values do not fit
your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and 
boolean, number, and enum parameters with values not fitting your use case).
*/

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.*;
import com.oracle.bmc.generativeaiinference.responses.*;
import java.math.BigDecimal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Date;
import java.util.UUID;
import java.util.Arrays;


public class GenerateTextExample {
    public static void main(String[] args) throws Exception {

        /**
         * Create a default authentication provider that uses the DEFAULT
         * profile in the configuration file.
         * Refer to <see href="https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File>the public documentation</see> on how to prepare a configuration file.
         */
        final ConfigFileReader.ConfigFile configFile = ConfigFileReader.parseDefault();
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        /* Create a service client */
        GenerativeAiInferenceClient client = GenerativeAiInferenceClient.builder().build(provider);

        /* Create a request and dependent object(s). */
	GenerateTextDetails generateTextDetails = GenerateTextDetails.builder()
		.compartmentId("ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value")
		.servingMode(OnDemandServingMode.builder()
			.modelId("ocid1.test.oc1..<unique_ID>EXAMPLE-modelId-Value").build())
		.inferenceRequest(CohereLlmInferenceRequest.builder()
			.prompt("EXAMPLE-prompt-Value")
			.isStream(true)
			.numGenerations(4)
			.isEcho(true)
			.maxTokens(361)
			.temperature(0.09766191)
			.topK(272)
			.topP(0.74587196)
			.frequencyPenalty(0.74314505)
			.presencePenalty(0.8300563)
			.stopSequences(new ArrayList<>(Arrays.asList("EXAMPLE--Value")))
			.returnLikelihoods(CohereLlmInferenceRequest.ReturnLikelihoods.All)
			.truncate(CohereLlmInferenceRequest.Truncate.None).build()).build();

	GenerateTextRequest generateTextRequest = GenerateTextRequest.builder()
		.generateTextDetails(generateTextDetails)
		.opcRetryToken("EXAMPLE-opcRetryToken-Value")
		.opcRequestId("1FQBD4A4P2Y10QA86JGW<unique_ID>").build();

        /* Send request to the Client */
        GenerateTextResponse response = client.generateText(generateTextRequest);
    }

    
}
```

```python
# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci

# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


# Initialize service client with default config file
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config)


# Send the request to service, some parameters are not required, see API
# doc for more info
generate_text_response = generative_ai_inference_client.generate_text(
    generate_text_details=oci.generative_ai_inference.models.GenerateTextDetails(
        compartment_id="ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value",
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
            serving_type="ON_DEMAND",
            model_id="ocid1.test.oc1..<unique_ID>EXAMPLE-modelId-Value"),
        inference_request=oci.generative_ai_inference.models.CohereLlmInferenceRequest(
            runtime_type="COHERE",
            prompt="EXAMPLE-prompt-Value",
            is_stream=True,
            num_generations=4,
            is_echo=True,
            max_tokens=361,
            temperature=0.09766191,
            top_k=272,
            top_p=0.74587196,
            frequency_penalty=0.74314505,
            presence_penalty=0.8300563,
            stop_sequences=["EXAMPLE--Value"],
            return_likelihoods="ALL",
            truncate="NONE")),
    opc_retry_token="EXAMPLE-opcRetryToken-Value",
    opc_request_id="1FQBD4A4P2Y10QA86JGW<unique_ID>")

# Get the data from response
print(generate_text_response.data)
```
SummarizeTextResult Reference
Summarize text result to return to caller.

Attributes
id
Required: yes
Type: string
A unique identifier for this SummarizeTextResult.

input
Required: no
Type: string
The original input. Only included if "isEcho" set to true.

modelId
Required: no
Type: string
The OCID of the model used in this inference request.

modelVersion
Required: no
Type: string
The version of the model.

summary
Required: yes
Type: string
Summary result corresponding to input.
SummarizeText GenerativeAiInference
​post /20231130/actions/summarizeText
Summarizes the input text.


Request
SummarizeText
Parameters
Name	Where	Description
opc-retry-token	
header

Required: no
Type: string
Min Length: 1
Max Length: 64
A token that uniquely identifies a request so it can be retried in case of a timeout or server error without risk of executing that same action again. Retry tokens expire after 24 hours, but can be invalidated before that, in case of conflicting operations. For example, if a resource is deleted and purged from the system, then a retry of the original creation request is rejected.

opc-request-id	
header

Required: no
Type: string
The client request ID for tracing.

Body
The request body must contain a single SummarizeTextDetails resource.

Examples
```java 
/** This is an automatically generated code sample. 
To make this code sample work in your Oracle Cloud tenancy, 
please replace the values for any parameters whose current values do not fit
your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and 
boolean, number, and enum parameters with values not fitting your use case).
*/

import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.generativeaiinference.GenerativeAiInferenceClient;
import com.oracle.bmc.generativeaiinference.model.*;
import com.oracle.bmc.generativeaiinference.requests.*;
import com.oracle.bmc.generativeaiinference.responses.*;
import java.math.BigDecimal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Date;
import java.util.UUID;
import java.util.Arrays;


public class SummarizeTextExample {
    public static void main(String[] args) throws Exception {

        /**
         * Create a default authentication provider that uses the DEFAULT
         * profile in the configuration file.
         * Refer to <see href="https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File>the public documentation</see> on how to prepare a configuration file.
         */
        final ConfigFileReader.ConfigFile configFile = ConfigFileReader.parseDefault();
        final AuthenticationDetailsProvider provider = new ConfigFileAuthenticationDetailsProvider(configFile);

        /* Create a service client */
        GenerativeAiInferenceClient client = GenerativeAiInferenceClient.builder().build(provider);

        /* Create a request and dependent object(s). */
	SummarizeTextDetails summarizeTextDetails = SummarizeTextDetails.builder()
		.input("EXAMPLE-input-Value")
		.servingMode(DedicatedServingMode.builder()
			.endpointId("ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value").build())
		.compartmentId("ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value")
		.isEcho(false)
		.temperature(2.548958)
		.additionalCommand("EXAMPLE-additionalCommand-Value")
		.length(SummarizeTextDetails.Length.Auto)
		.format(SummarizeTextDetails.Format.Auto)
		.extractiveness(SummarizeTextDetails.Extractiveness.Auto).build();

	SummarizeTextRequest summarizeTextRequest = SummarizeTextRequest.builder()
		.summarizeTextDetails(summarizeTextDetails)
		.opcRetryToken("EXAMPLE-opcRetryToken-Value")
		.opcRequestId("NKYOLRK1NK20W7HQVUVL<unique_ID>").build();

        /* Send request to the Client */
        SummarizeTextResponse response = client.summarizeText(summarizeTextRequest);
    }

    
}
```

```python
# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci

# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


# Initialize service client with default config file
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config)


# Send the request to service, some parameters are not required, see API
# doc for more info
summarize_text_response = generative_ai_inference_client.summarize_text(
    summarize_text_details=oci.generative_ai_inference.models.SummarizeTextDetails(
        input="EXAMPLE-input-Value",
        serving_mode=oci.generative_ai_inference.models.DedicatedServingMode(
            serving_type="DEDICATED",
            endpoint_id="ocid1.test.oc1..<unique_ID>EXAMPLE-endpointId-Value"),
        compartment_id="ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value",
        is_echo=False,
        temperature=2.548958,
        additional_command="EXAMPLE-additionalCommand-Value",
        length="AUTO",
        format="AUTO",
        extractiveness="AUTO"),
    opc_retry_token="EXAMPLE-opcRetryToken-Value",
    opc_request_id="NKYOLRK1NK20W7HQVUVL<unique_ID>")

# Get the data from response
print(summarize_text_response.data)
```

Pretrained Foundational Models in Generative AI
OCI Generative AI offers the following pretrained foundational models. Review the key features, regions, on-demand and dedicated AI cluster offerings, deprecation and retirement dates, and benchmarks for the models.

Chat Models
Ask questions and get conversational responses through an AI chat interface using the following chat models. Expand each section for the list of offered models in n OCI Generative AI.

Cohere Models
Cohere Command A (New)
Cohere Command R (08-2024)
Cohere Command R+ (08-2024)
Cohere Command R (Retired)
Cohere Command R+ (Retired)
Google Models
Google Gemini 2.5 Pro
Google Gemini 2.5 Flash
Google Gemini 2.5 Flash-Lite
Meta Models
Meta Llama 4 Maverick (New)
Meta Llama 4 Scout (New)
Meta Llama 3.3 (70B)
Meta Llama 3.2 90B Vision
Meta Llama 3.2 11B Vision
Meta Llama 3.1 (405B)
Meta Llama 3.1 (70B)
Meta Llama 3 (70B)
OpenAI Models (Beta)
OpenAI gpt-oss-120b (Beta)
OpenAI gpt-oss-20b (Beta)
xAI Models
xAI Grok Code Fast 1 (New)
xAI Grok 4 Fast (New)
xAI Grok 4
xAI Grok 3
xAI Grok 3 Mini
xAI Grok 3 Fast
xAI Grok 3 Mini Fast
Embed Models
Cohere Embed 4 (New)
Cohere Embed English Image 3
Cohere Embed English Light Image 3
Cohere Embed Multilingual Image 3
Cohere Embed Multilingual Light Image 3
Cohere Embed English 3
Cohere Embed English Light 3
Cohere Embed Multilingual 3
Cohere Embed Multilingual Light 3
Rerank Model
Cohere Rerank 3.5
Generation and Summarization Models (Deprecated)
Cohere Command (52B)
Cohere Command Light

Cohere Command A (New)
The cohere.command-a-03-2025 model is the most performant Cohere chat model to date with better throughput than cohere.command-r-08-2024. This model performs great for agentic enterprise tasks, and has significantly improved compute efficiency and has a 256,000 token context length.

Available in These Regions
Brazil East (Sao Paulo)
Germany Central (Frankfurt)
India South (Hyderabad)
Japan Central (Osaka)
Saudi Arabia Central (Riyadh)
UAE East (Dubai) (dedicated AI cluster only)
UK South (London)
US East (Ashburn) (dedicated AI cluster only)
US Midwest (Chicago)
Access this Model
Access this model through the Console, API, and the CLI:
Console
Inference API
Management API
Inference CLI
Management CLI
Key Features
The most performant Cohere chat model to date with better throughput than cohere.command-r-08-2024.
Excels at tool use, agents, retrieval augmented generation (RAG), and multilingual use cases.
Can maintain context from its long conversation history of 256,000 tokens.
Maximum prompt + response length: 256,000 tokens for each run.
For on-demand inferencing, the response length is capped at 4,000 tokens for each run.
For the dedicated mode, the response length isn't capped off and the context length is 256,000 tokens.
On-Demand Mode
This model is available on-demand in regions not listed as (dedicated AI cluster only). See the following table for this model's on-demand product name on the pricing page.

Model Name	OCI Model Name	Pricing Page Product Name
Cohere Command A	cohere.command-a-03-2025	Large Cohere
You can reach the pretrained foundational models in Generative AI through two modes: on-demand and dedicated. Here are key features for the on-demand mode:
You pay as you go for each inference call when you use the models in the playground or when you call the models through the API.

Low barrier to start using Generative AI.
Great for experimentation, proof of concept, and model evaluation.
Available for the pretrained models in regions not listed as (dedicated AI cluster only).
 Important

Dynamic Throttling Limit Adjustment for On-Demand Mode

OCI Generative AI dynamically adjusts the request throttling limit for each active tenancy based on model demand and system capacity to optimize resource allocation and ensure fair access.

This adjustment depends on the following factors:

The current maximum throughput supported by the target model.
Any unused system capacity at the time of adjustment.
Each tenancy’s historical throughput usage and any specified override limits set for that tenancy.
Note: Because of dynamic throttling, rate limits are undocumented and can change to meet system-wide demand.

 Tip

Because of the dynamic throttling limit adjustment, we recommend implementing a back-off strategy, which involves delaying requests after a rejection. Without one, repeated rapid requests can lead to further rejections over time, increased latency, and potential temporary blocking of client by the Generative AI service. By using a back-off strategy, such as an exponential back-off strategy, you can distribute requests more evenly, reduce load, and improve retry success, following industry best practices and enhancing the overall stability and performance of your integration to the service.

Dedicated AI Cluster for the Model
In the preceding region list, models in regions that aren't marked with (dedicated AI cluster only) have both on-demand and dedicated AI cluster options. For on-demand mode, you don't need clusters and you can reach the model in the Console playground or through the API.

To reach a model through a dedicated AI cluster in any listed region, you must create an endpoint for that model on a dedicated AI cluster. For the cluster unit size that matches this model, see the following table.

Base Model	Fine-Tuning Cluster	Hosting Cluster	Pricing Page Information	Request Cluster Limit Increase
Model Name: Cohere Command A
OCI Model Name: cohere.command-a-03-2025
Not available for fine-tuning	
Unit Size: LARGE_COHERE_V3
Required Units: 1
Pricing Page Product Name: Large Cohere - Dedicated
Limit Name: dedicated-unit-large-cohere-count
For Hosting, Request Limit Increase by: 1
Model Name: Cohere Command A (UAE East (Dubai) only)
OCI Model Name: cohere.command-a-03-2025
Not available for fine-tuning	
Unit Size: SMALL_COHERE_4
Required Units: 1
Pricing Page Product Name: Small Cohere - Dedicated
For Hosting, Multiply the Unit Price: x4
Limit Name: dedicated-unit-small-cohere-count
For Hosting, Request Limit Increase by: 4
 Tip

If you don't have enough cluster limits in your tenancy for hosting the Cohere Command A model on a dedicated AI cluster,
For the UAE East (Dubai) region, request the dedicated-unit-small-cohere-count limit to increase by 4.
For all other regions, request the dedicated-unit-large-cohere-count limit to increase by 1.
See Requesting a Service Limit Increase.

Endpoint Rules for Clusters
A dedicated AI cluster can hold up to 50 endpoints.
Use these endpoints to create aliases that all point either to the same base model or to the same version of a custom model, but not both types.
Several endpoints for the same model make it easy to assign them to different users or purposes.
Hosting Cluster Unit Size	Endpoint Rules
LARGE_COHERE_V3	
Base model: To run the cohere.command-a-03-2025 model on several endpoints, create as many endpoints as you need on a LARGE_COHERE_V3 cluster (unit‑size).
Custom model: You can't fine‑tune cohere.command‑a‑03‑2025, so you can't create and host custom models built from that base.
SMALL_COHERE_4 (UAE East (Dubai) only)	
Base model: To run the cohere.command-a-03-2025 model on several endpoints in UAE East (Dubai), create as many endpoints as you need on a SMALL_COHERE_4 cluster (unit‑size).
Custom model: You can't fine‑tune cohere.command‑a‑03‑2025, so you can't create and host custom models built from that base.
 Tip

To increase the call volume supported by a hosting cluster, increase its instance count by editing the dedicated AI cluster. See Updating a Dedicated AI Cluster.

For more than 50 endpoints per cluster, request an increase for the limit, endpoint-per-dedicated-unit-count. See Requesting a Service Limit Increase and Service Limits for Generative AI.

Cluster Performance Benchmarks
Review the Cohere Command A cluster performance benchmarks for different use cases.

Release and Retirement Dates
Model	Release Date	On-Demand Retirement Date	Dedicated Mode Retirement Date
cohere.command-a-03-2025	2025-05-14	At least one month after the release of the 1st replacement model.	At least 6 months after the release of the 1st replacement model.
 Important

For a list of all model time lines and retirement details, see Retiring the Models.
Model Parameters
To change the model responses, you can change the values of the following parameters in the playground or the API.

Maximum output tokens
The maximum number of tokens that you want the model to generate for each response. Estimate four characters per token. Because you're prompting a chat model, the response depends on the prompt and each response doesn't necessarily use up the maximum allocated tokens.

Preamble override
An initial context or guiding message for a chat model. When you don't give a preamble to a chat model, the default preamble for that model is used. You can assign a preamble in the Preamble override parameter, for the models. The default preamble for the Cohere family is:

You are Command.
            You are an extremely capable large language model built by Cohere. 
            You are given instructions programmatically via an API
            that you follow to the best of your ability.
Overriding the default preamble is optional. When specified, the preamble override replaces the default Cohere preamble. When adding a preamble, for best results, give the model context, instructions, and a conversation style.

 Tip

For chat models without the preamble override parameter, you can include a preamble in the chat conversation and directly ask the model to answer in a certain way.
Safety Mode
Adds a safety instruction for the model to use when generating responses. Options are:
Contextual: (Default) Puts fewer constraints on the output. It maintains core protections by aiming to reject harmful or illegal suggestions, but it allows profanity and some toxic content, sexually explicit and violent content, and content that contains medical, financial, or legal information. Contextual mode is suited for entertainment, creative, or academic use.
Strict: Aims to avoid sensitive topics, such as violent or sexual acts and profanity. This mode aims to provide a safer experience by prohibiting responses or recommendations that it finds inappropriate. Strict mode is suited for corporate use, such as for corporate communications and customer service.
Off: No safety mode is applied.
Temperature
The level of randomness used to generate the output text.

 Tip

Start with the temperature set to 0 or less than one, and increase the temperature as you regenerate the prompts for a more creative output. High temperatures can introduce hallucinations and factually incorrect information.
Top p
A sampling method that controls the cumulative probability of the top tokens to consider for the next token. Assign p a decimal number between 0 and 1 for the probability. For example, enter 0.75 for the top 75 percent to be considered. Set p to 1 to consider all tokens.

Top k
A sampling method in which the model chooses the next token randomly from the top k most likely tokens. A high value for k generates more random output, which makes the output text sound more natural. The default value for k is 0 for Cohere Command models and -1 for Meta Llama models, which means that the model should consider all tokens and not use this method.

Frequency penalty
A penalty that's assigned to a token when that token appears frequently. High penalties encourage fewer repeated tokens and produce a more random output.

For the Meta Llama family models, this penalty can be positive or negative. Positive numbers encourage the model to use new tokens and negative numbers encourage the model to repeat the tokens. Set to 0 to disable.

Presence penalty
A penalty that's assigned to each token when it appears in the output to encourage generating outputs with tokens that haven't been used.

Seed
A parameter that makes a best effort to sample tokens deterministically. When this parameter is assigned a value, the large language model aims to return the same result for repeated requests when you assign the same seed and parameters for the requests.

Allowed values are integers and assigning a large or a small seed value doesn't affect the result. Assigning a number for the seed parameter is similar to tagging the request with a number. The large language model aims to generate the same set of tokens for the same integer in consecutive requests. This feature is especially useful for debugging and testing. The seed parameter has no maximum value for the API, and in the Console, its maximum value is 9999. Leaving the seed value blank in the Console, or null in the API disables this feature.

 Warning

The seed parameter might not produce the same result in the long-run, because the model updates in the OCI Generative AI service might invalidate the seed. Cohere Command R (Retired)

Google Gemini 2.5 Pro
 Important

To ensure proper alignment with Oracle’s requirements, access to this model is limited to approved customers. To enable this model in your tenancy, contact your Oracle representative.

The Gemini 2.5 Pro model (google.gemini-2.5-pro) is a reasoning, multimodal model that excels at solving complex problems and is the most advanced reasoning Gemini model to date. This model is the next iteration and preforms better than the Gemini 2.0 series. The Gemini 2.5 Pro model is great at understanding large datasets and complex problems from different types of input, such as text, images, and code.

Available in This Region
US East (Ashburn) (Oracle Interconnect for Google Cloud only) and (on-demand only)
US Midwest (Chicago) (on-demand only)
US West (Phoenix) (on-demand only)
 Important

External Calls

The Google Gemini 2.5 models that can be accessed through the OCI Generative AI service, are hosted externally by Google. Therefore, a call to a Google Gemini model (through the OCI Generative AI service) results in a call to a Google location.

Key Features
Model Name in OCI Generative AI: google.gemini-2.5-pro
Available On-Demand: Access this model on-demand, through the Console playground or the API.
Multimodal Support: Input text, code, and images and get a text output. Audio and video file inputs are supported through API only. See Image Understanding, Audio Understanding and Video Understanding.
Knowledge: Has a deep domain knowledge in science, mathematics, and code.
Context Length: One million tokens
Maximum Input Tokens: 1,048,576 (Console and API)
Maximum Output Tokens: 65,536 (default) (Console and API)
Excels at These Use Cases: Applications that require powerful in-depth thinking, enhanced reasoning, detailed explanations and deep understanding, such as advanced coding, scientific analysis, and complex content extraction.
Has Reasoning: Yes. Also strong at visual reasoning and image understanding. For reasoning problems increase the maximum output tokens. See Model Parameters.
Knowledge Cutoff: January 2025
See the following table for the features supported in the Google Vertex AI Platform for OCI Generative, with links to each feature.

Supported Gemini 2.5 Pro Features
Feature	Supported?
Code execution	Yes
Tuning	No
System instructions	Yes
Structured output	Yes
Batch prediction	No
Function calling	Yes
Count Tokens	No
Thinking	Yes, but turning off the thinking process isn't supported.
Context caching	Yes, the model can cache the input tokens, but this feature isn't controlled through the API.
Vertex AI RAG Engine	No
Chat completions	Yes
For key feature details, see the Google Gemini 2.5 Pro documentation and the Google Gemini 2.5 Pro model card.

Image Understanding
Image Size
Console: Maximum image size: 5 MB
API: Maximum images per prompt: 3,000 and maximum image size before encoding: 7 MB
Supported Image Inputs
Console: png and jpeg formats
API: In the Chat operation submit a base64 encoded version of an image. For example, a 512 x 512 image typically converts to around 1,610 tokens. Supported MIME types are: image/png, image/jpeg, image/webp, image/heic, and image/heif. For the format, see ImageContent Reference.
Technical Details
Supports object detection and segmentation. See Image Understanding in the Gemini API documentation.
Audio Understanding
Supported Audio Formats
Console: not available
API: Supported media files are audio/wav, audio/mp3, audio/aiff, audio/aac, audio/ogg, and audio/flac.
Supported Audio Inputs for the API
URL: Convert a supported audio format to a base64 encoded version of the audio file.
URI: Submit the audio in a Uniform Resource Identifier (URI) format so without uploading the file, the model can access the audio.
For the format, see AudioContent Reference.

Technical Details
Token Conversion Each second of audio represents 32 tokens, so one minute of audio corresponds to 1,920 tokens.
Non‑speech Detection: The model can recognize non‑speech components such as bird songs and sirens.
Maximum Length: The maximum supported audio length in a single prompt is 9.5 hours. You can submit several files as long as their combined duration stays under 9.5 hours.
Downsampling: The model downsamples audio files to a 16 kbps resolution.
Channel Merging: If an audio source has several channels, the model merges them into a single channel.
See Audio Understanding in the Gemini API documentation.

Video Understanding
Supported Audio Formats
Console: not available
API: Supported media files are video/mp4, video/mpeg, video/mov, video/avi, video/x-flv, video/mpg, video/webm, video/wmv, and video/3gpp.
Supported Video Inputs for the API
URL: Convert a supported video format to a base64 encoded version of the video file.
URI: Submit the video in a Uniform Resource Identifier (URI) format so without uploading the file, the model can access the video.
For the format, see VideoContent Reference.

Technical Details
See Video Understanding in Gemini API documentation.

On-Demand Mode
 Note

The Gemini models are available only in the on-demand mode.
Model Name	OCI Model Name	Pricing Page Product Name
Gemini 2.5 Pro	google.gemini-2.5-pro	Google - Gemini 2.5 Pro
You can reach the pretrained foundational models in Generative AI through two modes: on-demand and dedicated. Here are key features for the on-demand mode:
You pay as you go for each inference call when you use the models in the playground or when you call the models through the API.

Low barrier to start using Generative AI.
Great for experimentation, proof of concept, and model evaluation.
Available for the pretrained models in regions not listed as (dedicated AI cluster only).
 Tip

We recommend implementing a back-off strategy, which involves delaying requests after a rejection. Without one, repeated rapid requests can lead to further rejections over time, increased latency, and potential temporary blocking of client by the Generative AI service. By using a back-off strategy, such as an exponential back-off strategy, you can distribute requests more evenly, reduce load, and improve retry success, following industry best practices and enhancing the overall stability and performance of your integration to the service.

Release Date
Model	Release Date	On-Demand Retirement Date	Dedicated Mode Retirement Date
google.gemini-2.5-pro	2025-10-01	Tentative	This model isn't available for the dedicated mode.
 Important

To learn about OCI Generative AI model deprecation and retirement, see Retiring the Models.
Model Parameters
To change the model responses, you can change the values of the following parameters in the playground or the API.

Maximum output tokens
The maximum number of tokens that you want the model to generate for each response. Estimate four characters per token. Because you're prompting a chat model, the response depends on the prompt and each response doesn't necessarily use up the maximum allocated tokens. The maximum prompt + output length is 128,000 tokens for each run.

 Tip

For large inputs with difficult problems, set a high value for the maximum output tokens parameter.
Temperature
The level of randomness used to generate the output text. Min: 0, Max: 2, Default: 1

 Tip

Start with the temperature set to 0 or less than one, and increase the temperature as you regenerate the prompts for a more creative output. High temperatures can introduce hallucinations and factually incorrect information.
Top p
A sampling method that controls the cumulative probability of the top tokens to consider for the next token. Assign p a decimal number between 0 and 1 for the probability. For example, enter 0.75 for the top 75 percent to be considered. Set p to 1 to consider all tokens.

Top k
A sampling method in which the model chooses the next token randomly from the top k most likely tokens. In the Gemini 2.5 models, the top k has a fixed value of 64, which means that the model considers only the 64 most likely tokens (words or word parts) for each step of generation. The final token is then chosen from this list.

Number of Generations (API only)
The numGenerations parameter in the API controls how many different response options the model generates for each prompt.

When you send a prompt, the Gemini model generates a set of possible answers. By default, it returns only the response with the highest probability (numGenerations = 1).
If you increase the numGenerations parameter to a number between or equal to 2 and 8 you can have the model generate 2 to 8 distinct responses.