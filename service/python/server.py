import asyncio
import websockets
import json
import os
import oci
from throttler import throttle
from pypdf import PdfReader
from io import BytesIO
from typing import Any, Dict, List
import re
from types import SimpleNamespace
from aiohttp import web

# TODO: Please update config profile name and use the compartmentId that has policies grant permissions for using Generative AI Service
compartment_id = "ocid1.compartment.oc1..aaaaaaaaut7vieqsewqr4nezosxg4ikf2mszg4roiimlbvhqtinrpgevy6uq"
CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file('~/.oci/config', CONFIG_PROFILE)

# Service endpoint
endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
INFERENCE_REGION = endpoint.split("inference.generativeai.")[-1].split(".oci.")[0]  # e.g., "us-chicago-1"
MODEL_ID = os.getenv("GENAI_ONDEMAND_MODEL_ID", "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyalrfnqiqipm3xn4yy2r2fww32yidtopep6rg2uupd3i2a")
ENDPOINT_ID = os.getenv("GENAI_ENDPOINT_ID")
generative_ai_inference_client = (
    oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )
)

# Management client for Generative AI (to resolve model aliases to OCIDs)
mgmt_endpoint = f"https://generativeai.{INFERENCE_REGION}.oci.oraclecloud.com"
generative_ai_mgmt_client = oci.generative_ai.GenerativeAiClient(
    config=config,
    service_endpoint=mgmt_endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy(),
    timeout=(10, 60),
)

def resolve_model_id(model_key: str) -> str:
    # If OCID provided, ensure region matches inference region; otherwise attempt alias fallback
    if model_key and model_key.startswith("ocid1."):
        if f".{INFERENCE_REGION}." in model_key:
            return model_key
        else:
            print(f"[WARN] Provided model OCID region does not match inference region {INFERENCE_REGION}: {model_key}")
            # Try default Cohere Command A alias in this region
            model_key = "cohere.command-a-03-2025"
    try:
        resp = generative_ai_mgmt_client.list_models(compartment_id=compartment_id)
        models = getattr(resp.data, "items", [])

        # Helper to check if an OCID contains the region token (e.g., ".us-chicago-1.")
        def ocid_has_region(ocid: str, region: str) -> bool:
            return ocid and f".{region}." in ocid

        # 1) Exact display name match in same region
        for m in models:
            name = getattr(m, "display_name", None) or getattr(m, "name", None)
            mid = getattr(m, "id", None)
            if name and mid and name.lower() == model_key.lower() and ocid_has_region(mid, INFERENCE_REGION):
                return mid

        # 2) Partial display name match in same region
        for m in models:
            name = getattr(m, "display_name", None) or getattr(m, "name", None)
            mid = getattr(m, "id", None)
            if name and mid and model_key.lower() in name.lower() and ocid_has_region(mid, INFERENCE_REGION):
                return mid

        # 3) Exact display name match (any region) as last resort
        for m in models:
            name = getattr(m, "display_name", None) or getattr(m, "name", None)
            if name and name.lower() == model_key.lower():
                print(f"[WARN] Resolved model '{name}' but OCID region does not match {INFERENCE_REGION}: {m.id}")
                return m.id

        # 4) Fallback: return the alias as-is
        print(f"[WARN] Could not resolve model alias '{model_key}' to an OCID in compartment {compartment_id} for region {INFERENCE_REGION}. Using alias as-is.")
        return model_key
    except Exception as e:
        print(f"[WARN] list_models failed while resolving model '{model_key}': {e}. Using alias as-is.")
        return model_key

RESOLVED_MODEL_ID = resolve_model_id(MODEL_ID)
print(f"RESOLVED_MODEL_ID: {RESOLVED_MODEL_ID}")

# Cache models list for vendor lookup
MODELS_CACHE = {}
try:
    resp = generative_ai_mgmt_client.list_models(compartment_id=compartment_id)
    models = getattr(resp.data, "items", []) or []
    for m in models:
        mid = getattr(m, "id", None)
        vendor = getattr(m, "vendor", "").lower()
        if mid:
            MODELS_CACHE[mid] = vendor
    print(f"Cached {len(MODELS_CACHE)} models for vendor lookup")
except Exception as e:
    print(f"Warning: Failed to cache models list: {e}")

@throttle(rate_limit=15, period=65.0)
async def generate_ai_response(prompts, override_model_id=None):
    effective_model_id = RESOLVED_MODEL_ID if override_model_id is None else resolve_model_id(override_model_id)
    print(f"Effective model ID: {effective_model_id}")

    # Determine vendor from cached models
    vendor = MODELS_CACHE.get(effective_model_id, "cohere").lower()  # Default to cohere
    print(f"Model vendor: {vendor}")

    # Use Chat API for all models since they are primarily chat models
    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    if vendor == "cohere":
        print(f"Using CohereChatRequest for model: {effective_model_id}")
        chat_request = oci.generative_ai_inference.models.CohereChatRequest()
        chat_request.message = prompts
        chat_request.max_tokens = 1000
        chat_request.temperature = 0.75
        chat_request.top_p = 0.7
        chat_request.frequency_penalty = 1.0
    else:
        print(f"Using GenericChatRequest for model: {effective_model_id}")
        chat_request = oci.generative_ai_inference.models.GenericChatRequest()
        # For Meta and xAI models, content must be a list of ChatContent objects
        # Create content as a list with TextContent
        text_content = {"type": "TEXT", "text": prompts}
        user_message = {
            "role": "USER",
            "content": [text_content]
        }
        chat_request.messages = [user_message]
        chat_request.max_tokens = 1000
        chat_request.temperature = 0.75
        chat_request.top_p = 0.7

    # Prefer Dedicated if provided; default to OnDemand for local dev to avoid 404 on missing endpoint
    if ENDPOINT_ID:
        chat_detail.serving_mode = oci.generative_ai_inference.models.DedicatedServingMode(endpoint_id=ENDPOINT_ID)
    else:
        chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=effective_model_id)

    chat_detail.compartment_id = compartment_id
    chat_detail.chat_request = chat_request

    if "<compartment_ocid>" in compartment_id:
        print("ERROR:Please update your compartment id in target python file")
        quit()

    try:
        chat_response = generative_ai_inference_client.chat(chat_detail)
        # Print result
        print("**************************Chat Result**************************")
        print(vars(chat_response))

        # Normalize response format - different vendors return different structures
        try:
            if hasattr(chat_response.data.chat_response, 'text'):
                # Cohere format
                normalized_text = chat_response.data.chat_response.text
            elif hasattr(chat_response.data.chat_response, 'choices') and chat_response.data.chat_response.choices:
                # Generic format (Meta, xAI)
                choice = chat_response.data.chat_response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                    if isinstance(content, list) and content:
                        # Extract text from first content item (TextContent object)
                        first_content = content[0]
                        if hasattr(first_content, 'text'):
                            normalized_text = first_content.text
                        else:
                            normalized_text = str(first_content)
                    else:
                        normalized_text = str(content)
                else:
                    normalized_text = str(choice)
            else:
                normalized_text = str(chat_response.data.chat_response)

            # Store normalized text for consistent access
            chat_response.data.chat_response.text = normalized_text
        except Exception as parse_error:
            print(f"Error parsing response: {parse_error}")
            # Fallback to string representation
            chat_response.data.chat_response.text = str(chat_response.data.chat_response)

        return chat_response
    except Exception as e:
        print(f"Error calling chat API: {e}")
        return None

@throttle(rate_limit=15, period=65.0)
async def generate_ai_summary(summary_txt, prompt, override_model_id=None):
    effective_model_id = RESOLVED_MODEL_ID if override_model_id is None else resolve_model_id(override_model_id)

    # Use chat API for summarization since dedicated summarization API may not be available
    # Craft a comprehensive summarization prompt
    if prompt and prompt.strip():
        # Use custom prompt if provided
        summarization_prompt = f"{prompt}\n\nText to summarize:\n{summary_txt}"
    else:
        # Default comprehensive summarization prompt
        summarization_prompt = f"""Please provide a comprehensive summary of the following text. Include:

1. Main topics and key points
2. Important details and findings
3. Any conclusions or recommendations
4. Key data or statistics mentioned

Be concise but thorough. Structure your summary with clear headings if appropriate.

Text to summarize:
{summary_txt}"""

    print(f"Using chat API for summarization with model: {effective_model_id}")

    # Use the same chat API logic as generate_ai_response
    vendor = MODELS_CACHE.get(effective_model_id, "cohere").lower()

    # Use Chat API for summarization
    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    if vendor == "cohere":
        print(f"Using CohereChatRequest for summarization with model: {effective_model_id}")
        chat_request = oci.generative_ai_inference.models.CohereChatRequest()
        chat_request.message = summarization_prompt
        chat_request.max_tokens = 2000  # Allow longer responses for summaries
        chat_request.temperature = 0.3  # Lower temperature for more focused summaries
        chat_request.top_p = 0.7
        chat_request.frequency_penalty = 1.0
    else:
        print(f"Using GenericChatRequest for summarization with model: {effective_model_id}")
        chat_request = oci.generative_ai_inference.models.GenericChatRequest()
        # For Meta and xAI models, content must be a list of ChatContent objects
        text_content = {"type": "TEXT", "text": summarization_prompt}
        user_message = {
            "role": "USER",
            "content": [text_content]
        }
        chat_request.messages = [user_message]
        chat_request.max_tokens = 2000  # Allow longer responses for summaries
        chat_request.temperature = 0.3  # Lower temperature for more focused summaries
        chat_request.top_p = 0.7

    # Prefer Dedicated if provided; default to OnDemand for local dev
    if ENDPOINT_ID:
        chat_detail.serving_mode = oci.generative_ai_inference.models.DedicatedServingMode(endpoint_id=ENDPOINT_ID)
    else:
        chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=effective_model_id)

    chat_detail.compartment_id = compartment_id
    chat_detail.chat_request = chat_request

    if "<compartment_ocid>" in compartment_id:
        print("ERROR:Please update your compartment id in target python file")
        quit()

    try:
        chat_response = generative_ai_inference_client.chat(chat_detail)
        # Print result
        print("**************************Summarization Chat Result**************************")
        print(vars(chat_response))

        # Normalize response format - different vendors return different structures
        try:
            if hasattr(chat_response.data.chat_response, 'text'):
                # Cohere format
                summary_text = chat_response.data.chat_response.text
            elif hasattr(chat_response.data.chat_response, 'choices') and chat_response.data.chat_response.choices:
                # Generic format (Meta, xAI)
                choice = chat_response.data.chat_response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                    if isinstance(content, list) and content:
                        # Extract text from first content item (TextContent object)
                        first_content = content[0]
                        if hasattr(first_content, 'text'):
                            summary_text = first_content.text
                        else:
                            summary_text = str(first_content)
                    else:
                        summary_text = str(content)
                else:
                    summary_text = str(choice)
            else:
                summary_text = str(chat_response.data.chat_response)

        except Exception as parse_error:
            print(f"Error parsing summarization response: {parse_error}")
            summary_text = str(chat_response.data.chat_response)

        return {"summary": summary_text}

    except Exception as e:
        print(f"Summarization chat error: {e}")
        return {"summary": f"Error during summarization: {str(e)}"}

async def parse_pdf(file: BytesIO) -> List[str]:
    try:
        # Check if it's actually a PDF by looking at the first few bytes
        file.seek(0)
        header = file.read(8)
        if not header.startswith(b'%PDF-'):
            raise ValueError("File is not a valid PDF")

        file.seek(0)  # Reset file pointer
        pdf = PdfReader(file)
        output = []
        for page in pdf.pages:
            text = page.extract_text()
            # Merge hyphenated words
            text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
            # Fix newlines in the middle of sentences
            text = re.sub(r"(?<!\n\s)\n(?!\s\n)", " ", text.strip())
            # Remove multiple newlines
            text = re.sub(r"\n\s*\n", "\n\n", text)
            output.append(text)
        return output
    except Exception as e:
        print(f"PDF parsing error: {e}")
        # If PDF parsing fails, try to extract text from the raw bytes as if it were text
        try:
            file.seek(0)
            content = file.read().decode('utf-8', errors='ignore')
            # Clean up the content
            content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags
            content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
            return [content[:10000]]  # Limit to first 10k chars
        except Exception as text_error:
            print(f"Text extraction fallback also failed: {text_error}")
            return ["Error: Unable to extract text from uploaded file. Please ensure it's a valid PDF or text file."]

async def handle_websocket(websocket, path):
    try:
        while True:
            data = await websocket.recv()
            if isinstance(data, str):
                # if we are dealing with text, make it JSON
                try:
                    objData = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
                    if hasattr(objData, 'msgType') and objData.msgType == "question":
                        prompt = getattr(objData, 'data', '')
                        override = getattr(objData, "modelId", None)
                        response = await generate_ai_response(prompt, override)
                        if response and hasattr(response, 'data') and response.data:
                            answer = getattr(response.data.chat_response, 'text', 'No response')
                            buidJSON = {"msgType":"answer","data":answer}
                            await websocket.send(json.dumps(buidJSON))
                        else:
                            error_msg = {"msgType":"answer","data":"Error: No response from AI service"}
                            await websocket.send(json.dumps(error_msg))
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                except Exception as e:
                    print(f"WebSocket message processing error: {e}")
            # if it's not text, we have a binary and we will treat it as a PDF
            if not isinstance(data, str):
                try:
                    # split the ArrayBuffer into metadata and the actual PDF file
                    objData = data.split(b'\r\n\r\n')
                    # decode the metadata and parse the JSON data.  Creating Dict properties from the JSON
                    metadata = json.loads(objData[0].decode('utf-8'), object_hook=lambda d: SimpleNamespace(**d))
                    pdfFileObj = BytesIO(objData[1])
                    output = await parse_pdf(pdfFileObj)
                    override = getattr(metadata, "modelId", None)
                    response = await generate_ai_summary(''.join(output), getattr(metadata, 'msgPrompt', ''), override)
                    if response and 'summary' in response:
                        summary = response['summary']
                        buidJSON = {"msgType":"summary","data": summary}
                        await websocket.send(json.dumps(buidJSON))
                    else:
                        error_msg = {"msgType":"summary","data":"Error processing PDF"}
                        await websocket.send(json.dumps(error_msg))
                except Exception as e:
                    print(f"PDF processing error: {e}")
    except websockets.exceptions.ConnectionClosedOK as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"WebSocket handler error: {e}")


async def start_ws_server():
    # Start WebSocket server for chat/summarization
    return await websockets.serve(handle_websocket, "0.0.0.0", 1986, max_size=200000000)

async def list_models_http(request):
    try:
        resp = generative_ai_mgmt_client.list_models(compartment_id=compartment_id)
        models = getattr(resp.data, "items", []) or []

        def ocid_has_region(ocid: str, region: str) -> bool:
            return ocid and f".{region}." in ocid

        out = []
        for m in models:
            mid = getattr(m, "id", None)
            if not ocid_has_region(mid, INFERENCE_REGION):
                continue
            name = getattr(m, "display_name", None) or getattr(m, "name", None) or ""
            vendor = getattr(m, "vendor", "")
            version = getattr(m, "version", "")
            capabilities = getattr(m, "capabilities", []) or []
            time_created = str(getattr(m, "time_created", ""))
            out.append({
                "id": mid,
                "name": name,
                "vendor": vendor,
                "version": version,
                "capabilities": capabilities,
                "timeCreated": time_created
            })
        # Default: only chat-capable. Comment out filter below to return all models.
        out = [x for x in out if any(str(c).upper() == "CHAT" for c in x["capabilities"])]
        return web.json_response(out, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def generate_text_http(request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        model_id = body.get("modelId")
        resp = await generate_ai_response(prompt, model_id)
        # For chat responses, extract text from chat_response
        answer = resp.data.chat_response.text
        return web.json_response({"text": answer}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def summarize_text_http(request):
    try:
        body = await request.json()
        text = body.get("text", "")
        cmd = body.get("prompt", "")
        model_id = body.get("modelId")
        resp = await generate_ai_summary(text, cmd, model_id)
        summary = resp.summary
        return web.json_response({"summary": summary}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})

async def start_http_server():
    app = web.Application()
    app.router.add_get("/models", list_models_http)
    app.router.add_post("/generate", generate_text_http)
    app.router.add_post("/summarize", summarize_text_http)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 1987)
    await site.start()
    return runner

async def main():
    await start_ws_server()
    await start_http_server()
    print("Python adapter running: ws://localhost:1986, http://localhost:1987")
    # Run forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
