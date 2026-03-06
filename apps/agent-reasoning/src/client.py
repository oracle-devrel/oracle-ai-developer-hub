import json
import time
import requests
import sys

class OllamaClient:
    MAX_RETRIES = 3
    RETRY_BACKOFF = [2, 5, 10]  # seconds between retries

    def __init__(self, model="gemma3:270m", base_url="http://localhost:11434"):
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

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(url, json=data, stream=stream, timeout=300)
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
                return  # Success - exit retry loop

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_BACKOFF[attempt]
                    print(f"Ollama request failed (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {wait}s: {e}", file=sys.stderr)
                    time.sleep(wait)
                else:
                    print(f"Ollama request failed after {self.MAX_RETRIES} attempts: {e}", file=sys.stderr)
                    yield ""
