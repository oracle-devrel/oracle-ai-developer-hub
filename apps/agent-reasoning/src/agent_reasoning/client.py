import json
import requests
import sys

class OllamaClient:
    def __init__(self, model="gemma3:latest", base_url=None):
        if base_url is None:
            from agent_reasoning.config import get_ollama_host
            base_url = get_ollama_host()
        self.model = model
        self.base_url = base_url

    def generate(self, prompt, system=None, stream=True, temperature=0.7, top_k=40, top_p=0.9, num_predict=2048, stop=None):
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "num_predict": num_predict
        }
        if stop:
            data["stop"] = stop
        if system:
            data["system"] = system

        try:
            response = requests.post(url, json=data, stream=stream)
            response.raise_for_status()

            full_response = ""
            if stream:
                for line in response.iter_lines():
                    if line:
                        body = json.loads(line)
                        if "response" in body:
                            content = body["response"]
                            yield content
                            full_response += content
                        if body.get("done", False):
                            break
            else:
                body = response.json()
                yield body.get("response", "")

        except requests.exceptions.RequestException as e:
            error_msg = f"[OllamaClient] Error communicating with Ollama (model={self.model}): {e}"
            print(error_msg, file=sys.stderr)
            print(error_msg)  # Also print to stdout so it's visible in logs
            yield f"Error: Could not reach Ollama model '{self.model}'. Please check the model is available (ollama list)."
