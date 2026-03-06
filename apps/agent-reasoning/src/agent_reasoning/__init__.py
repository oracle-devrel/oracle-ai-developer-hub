"""
Agent Reasoning: Transform LLMs into robust problem-solving agents.

Usage:
    from agent_reasoning import ReasoningInterceptor
    from agent_reasoning.agents import CoTAgent, ToTAgent
    from agent_reasoning.ensemble import ReasoningEnsemble
    from agent_reasoning.config import get_ollama_host, set_ollama_host
"""

from agent_reasoning.interceptor import ReasoningInterceptor, AGENT_MAP
from agent_reasoning.client import OllamaClient
from agent_reasoning.ensemble import ReasoningEnsemble
from agent_reasoning.config import get_ollama_host, set_ollama_host, load_config, save_config

__version__ = "1.0.7"
__all__ = [
    "ReasoningInterceptor", 
    "ReasoningEnsemble", 
    "OllamaClient", 
    "AGENT_MAP",
    "get_ollama_host",
    "set_ollama_host",
    "load_config",
    "save_config",
]
