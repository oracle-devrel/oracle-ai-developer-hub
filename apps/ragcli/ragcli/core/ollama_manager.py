"""Ollama model management and auto-detection for ragcli."""

import requests
from typing import List, Dict, Any, Optional
from ragcli.config.config_manager import load_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


def list_available_models(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Query Ollama API to list all available models.
    
    Returns:
        Dict with 'models' list containing model information
    """
    if config is None:
        config = load_config()
    
    endpoint = config['ollama']['endpoint']
    timeout = config['ollama'].get('timeout', 30)
    
    try:
        response = requests.get(
            f"{endpoint}/api/tags",
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        return {"models": []}


def get_model_info(model_name: str, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific model.
    
    Args:
        model_name: Name of the model to query
        config: Configuration dict
    
    Returns:
        Model information dict or None if not found
    """
    models_data = list_available_models(config)
    
    for model in models_data.get('models', []):
        if model['name'] == model_name or model['name'].startswith(f"{model_name}:"):
            return model
    
    return None


def validate_model(model_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a model exists in Ollama.
    
    Args:
        model_name: Name of the model to validate
        config: Configuration dict
    
    Returns:
        True if model exists, False otherwise
    """
    model_info = get_model_info(model_name, config)
    return model_info is not None


def get_embedding_models(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Get list of available embedding models.
    
    Returns:
        List of embedding model names
    """
    models_data = list_available_models(config)
    embedding_models = []
    
    for model in models_data.get('models', []):
        model_name = model['name']
        # Simple heuristic: models with 'embed' in name are embedding models
        if 'embed' in model_name.lower():
            embedding_models.append(model_name)
    
    return embedding_models


def get_chat_models(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Get list of available chat/completion models.
    
    Returns:
        List of chat model names
    """
    models_data = list_available_models(config)
    chat_models = []
    
    for model in models_data.get('models', []):
        model_name = model['name']
        # Exclude embedding models
        if 'embed' not in model_name.lower():
            chat_models.append(model_name)
    
    return chat_models


def auto_select_embedding_model(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Auto-select best available embedding model.
    
    Preference order:
    1. nomic-embed-text (recommended)
    2. all-minilm
    3. mxbai-embed-large
    4. Any other embedding model
    
    Returns:
        Model name or None if no embedding models available
    """
    if config is None:
        config = load_config()
    
    available_models = get_embedding_models(config)
    
    if not available_models:
        logger.warning("No embedding models found in Ollama")
        return None
    
    # Check preference order
    preferences = [
        'nomic-embed-text',
        'all-minilm',
        'mxbai-embed-large'
    ]
    
    for pref in preferences:
        for model in available_models:
            if pref in model:
                logger.info(f"Auto-selected embedding model: {model}")
                return model
    
    # Fall back to first available
    selected = available_models[0]
    logger.info(f"Auto-selected embedding model (fallback): {selected}")
    return selected


def auto_select_chat_model(config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Auto-select best available chat model.
    
    Preference order:
    1. Configured model (if available)
    2. deepseek variants
    3. llama3 variants
    4. Any other chat model
    
    Returns:
        Model name or None if no chat models available
    """
    if config is None:
        config = load_config()
    
    available_models = get_chat_models(config)
    
    if not available_models:
        logger.warning("No chat models found in Ollama")
        return None
    
    # Check if configured model exists
    configured = config['ollama'].get('chat_model')
    if configured:
        for model in available_models:
            if configured in model:
                logger.info(f"Using configured chat model: {model}")
                return model
    
    # Check preference order
    preferences = ['qwen3.5', 'qwen3', 'gemma3', 'gemma', 'deepseek', 'llama3', 'llama2', 'mistral']
    
    for pref in preferences:
        for model in available_models:
            if pref in model.lower():
                logger.info(f"Auto-selected chat model: {model}")
                return model
    
    # Fall back to first available
    selected = available_models[0]
    logger.info(f"Auto-selected chat model (fallback): {selected}")
    return selected


def validate_config_models(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate that configured models exist in Ollama.
    
    Returns:
        Dict with validation results and warnings
    """
    if config is None:
        config = load_config()
    
    results = {
        'embedding_model_valid': False,
        'chat_model_valid': False,
        'warnings': [],
        'suggestions': {}
    }
    
    embedding_model = config['ollama']['embedding_model']
    chat_model = config['ollama']['chat_model']
    
    # Validate embedding model
    if validate_model(embedding_model, config):
        results['embedding_model_valid'] = True
        logger.info(f"Embedding model '{embedding_model}' is available")
    else:
        results['warnings'].append(f"Embedding model '{embedding_model}' not found in Ollama")
        # Suggest alternative
        alt = auto_select_embedding_model(config)
        if alt:
            results['suggestions']['embedding_model'] = alt
            logger.warning(f"Consider using '{alt}' instead")
    
    # Validate chat model
    if validate_model(chat_model, config):
        results['chat_model_valid'] = True
        logger.info(f"Chat model '{chat_model}' is available")
    else:
        results['warnings'].append(f"Chat model '{chat_model}' not found in Ollama")
        # Suggest alternative
        alt = auto_select_chat_model(config)
        if alt:
            results['suggestions']['chat_model'] = alt
            logger.warning(f"Consider using '{alt}' instead")
    
    return results

