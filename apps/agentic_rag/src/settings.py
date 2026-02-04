"""
Settings API for Agentic RAG System.

Provides endpoints to configure:
- Active LLM model (default: gemma3:latest)
- Model parameters
- System preferences
"""

import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

router = APIRouter(prefix="/v1/settings", tags=["Settings"])


class ModelSetting(BaseModel):
    """Current model configuration."""
    model_name: str
    description: Optional[str] = None


class SettingsResponse(BaseModel):
    """Full settings response."""
    model: ModelSetting
    available_models: List[str]


class UpdateModelRequest(BaseModel):
    """Request to update the active model."""
    model_name: str


# Global settings state
_current_settings = {
    "model_name": os.getenv("DEFAULT_MODEL", "gemma3:latest"),
}

# Callback functions to update components when settings change
_on_model_change_callbacks = []


def register_model_change_callback(callback):
    """Register a callback to be called when model changes."""
    _on_model_change_callbacks.append(callback)


def get_current_model() -> str:
    """Get the current active model name."""
    return _current_settings["model_name"]


def set_current_model(model_name: str):
    """Set the current active model name."""
    _current_settings["model_name"] = model_name
    # Notify all registered callbacks
    for callback in _on_model_change_callbacks:
        try:
            callback(model_name)
        except Exception as e:
            print(f"Error in model change callback: {e}")


def get_available_ollama_models() -> List[str]:
    """Get list of available Ollama models."""
    try:
        import ollama
        models_response = ollama.list()
        models = []

        # Handle different ollama library response formats
        # Newer ollama library returns ListResponse object with .models attribute
        if hasattr(models_response, 'models'):
            model_list = models_response.models
        elif isinstance(models_response, dict) and "models" in models_response:
            model_list = models_response["models"]
        else:
            model_list = []

        for model in model_list:
            # Handle both dict and object formats
            if hasattr(model, 'model'):
                model_name = model.model
            elif isinstance(model, dict) and "name" in model:
                model_name = model["name"]
            else:
                model_name = str(model)

            if model_name:
                models.append(model_name)

        return sorted(models)
    except Exception as e:
        print(f"Error listing Ollama models: {e}")
        return ["gemma3:latest", "gemma3:270m", "llama3:latest", "mistral:latest"]


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings including active model and available models."""
    available_models = get_available_ollama_models()
    return SettingsResponse(
        model=ModelSetting(
            model_name=_current_settings["model_name"],
            description=f"Currently using {_current_settings['model_name']} for reasoning"
        ),
        available_models=available_models
    )


@router.get("/model")
async def get_current_model_endpoint():
    """Get the current active model."""
    return {
        "model_name": _current_settings["model_name"]
    }


@router.post("/model")
async def update_model(request: UpdateModelRequest):
    """
    Update the active LLM model.

    This will reinitialize the reasoning ensemble and local agent
    with the new model.
    """
    # Validate model exists in Ollama
    available = get_available_ollama_models()

    # Allow any model name (Ollama will handle errors)
    old_model = _current_settings["model_name"]
    set_current_model(request.model_name)

    return {
        "success": True,
        "previous_model": old_model,
        "current_model": request.model_name,
        "message": f"Model updated from {old_model} to {request.model_name}"
    }


@router.get("/models")
async def list_available_models():
    """List all available Ollama models."""
    models = get_available_ollama_models()
    return {
        "models": models,
        "count": len(models),
        "current": _current_settings["model_name"]
    }


@router.post("/model/test")
async def test_model(request: UpdateModelRequest):
    """
    Test if a model is available and working.

    Sends a simple prompt to verify the model responds.
    """
    try:
        import ollama

        # Simple test prompt
        response = ollama.generate(
            model=request.model_name,
            prompt="Say 'OK' if you can hear me.",
            options={"num_predict": 10}
        )

        return {
            "success": True,
            "model": request.model_name,
            "response": response.get("response", "")[:100],
            "message": f"Model {request.model_name} is working"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "model": request.model_name,
                "error": str(e),
                "message": f"Model {request.model_name} failed: {str(e)}"
            }
        )
