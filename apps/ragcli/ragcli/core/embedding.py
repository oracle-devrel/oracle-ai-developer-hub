"""Embedding and LLM generation via Ollama API for ragcli."""

import requests
import json
from typing import List, Dict, Any, Generator, Optional, Callable
from ragcli.config.config_manager import load_config
from ..utils.helpers import retry_with_backoff
from ..utils.logger import get_logger

logger = get_logger(__name__)

def generate_embedding(text: str, model: str, config: dict, progress_callback: Optional[Callable] = None, conn=None) -> List[float]:
    """Generate embedding for text using Ollama API or OracleEmbeddings."""
    
    # Check if using Oracle embeddings
    # We use 'database' provider as default for on-db models, or others if specified
    use_oracle_embeddings = config.get('vector_index', {}).get('use_oracle_embeddings', False)
    
    if conn and use_oracle_embeddings:
        try:
            from .oracle_integration import OracleIntegrationManager
            manager = OracleIntegrationManager(conn)
            
            # Params for OracleEmbeddings
            params = config.get('vector_index', {}).get('oracle_embedding_params', {
                "provider": "database", 
                "model": "all_minilm_l12_v2" # Default on-db model alias
            })
            
            # Override model if passed explicitly and not default
            # But usually 'model' arg here comes from config['ollama']['embedding_model'] which might be 'nomic-embed-text'
            # If we are using Oracle, we ignore the local ollama model requirement
            
            embeddings = manager.generate_embeddings([text], params=params)
            if embeddings:
                return embeddings[0]
        except Exception as e:
            logger.error(f"Oracle embedding failed: {e}")
            # Fallback to Ollama or raise? Let's fallback or raise. 
            # If explicit config for Oracle, we should probably fail if it doesn't work.
            if config.get('vector_index', {}).get('strict_oracle_embeddings', False):
                raise
    
    # Fallback / Default: Ollama
    endpoint = config['ollama']['endpoint']
    timeout = config['ollama']['timeout']

    def _api_call():
        payload = {
            "model": model,
            "prompt": text
        }
        response = requests.post(
            f"{endpoint}/api/embeddings",
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()["embedding"]

    try:
        result = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0, max_delay=10.0)
        if progress_callback:
            progress_callback()
        return result
    except Exception as e:
        logger.error(f"Failed to generate embedding for model {model}", exc_info=True)
        raise Exception(f"Embedding generation failed: {e}")


def batch_generate_embeddings(
    texts: List[str],
    model: str,
    config: dict,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    conn=None
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts with progress tracking.
    """
    use_oracle_embeddings = config.get('vector_index', {}).get('use_oracle_embeddings', False)
    
    if conn and use_oracle_embeddings:
        # Use batch capability of OracleEmbeddings
        try:
            from .oracle_integration import OracleIntegrationManager
            manager = OracleIntegrationManager(conn)
            params = config.get('vector_index', {}).get('oracle_embedding_params', {
                "provider": "database", 
                "model": "all_minilm_l12_v2"
            })
            
            embeddings = manager.generate_embeddings(texts, params=params)
             
            # Update progress manually since it's one call
            if progress_callback:
                progress_callback(len(texts), len(texts))
                
            return embeddings
        except Exception as e:
            logger.error(f"Oracle batch embedding failed: {e}")
            if config.get('vector_index', {}).get('strict_oracle_embeddings', False):
                raise

    embeddings = []
    total = len(texts)
    
    for i, text in enumerate(texts, 1):
        embedding = generate_embedding(text, model, config, conn=conn) # conn passed but individual call reuse logic
        embeddings.append(embedding)
        
        if progress_callback:
            progress_callback(i, total)
    
    return embeddings

def generate_response(
    messages: List[Dict[str, str]],
    model: str,
    config: dict,
    stream: bool = False
) -> Optional[Generator[str, None, None]]:
    """Generate response using Ollama chat API with retry logic."""
    endpoint = config['ollama']['endpoint']
    timeout = config['ollama']['timeout']

    def _api_call():
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
        }
        response = requests.post(
            f"{endpoint}/api/chat",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def _streaming_call():
        """True streaming using Ollama's native format."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }
        response = requests.post(
            f"{endpoint}/api/chat",
            json=payload,
            timeout=timeout,
            stream=True
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                # Ollama native format: {"message": {"content": "token"}, "done": false}
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token

    try:
        if stream:
            return _streaming_call()
        else:
            result = retry_with_backoff(_api_call, max_retries=3, base_delay=1.0, max_delay=10.0)
            return result
    except Exception as e:
        logger.error(f"Failed to generate response for model {model}", exc_info=True)
        raise Exception(f"Response generation failed: {e}")

# TODO: Add token counting, OpenAI-compatible endpoint support, more error handling
