import logging
from src.agents.standard import StandardAgent
from src.agents.cot import CoTAgent
from src.agents.self_reflection import SelfReflectionAgent
from src.agents.react import ReActAgent
from src.agents.tot import ToTAgent
from src.agents.recursive import RecursiveAgent
from src.agents.consistency import ConsistencyAgent
from src.agents.decomposed import DecomposedAgent
from src.agents.least_to_most import LeastToMostAgent
from src.agents.refinement_loop import RefinementLoopAgent
from src.agents.complex_refinement import ComplexRefinementLoopAgent

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReasoningInterceptor")

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "chain_of_thought": CoTAgent,
    "reflection": SelfReflectionAgent,
    "self_reflection": SelfReflectionAgent,
    "react": ReActAgent,
    "tot": ToTAgent,
    "tree_of_thoughts": ToTAgent,
    "recursive": RecursiveAgent,
    "rlm": RecursiveAgent,
    "consistency": ConsistencyAgent,
    "self_consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
    "ltm": LeastToMostAgent,
    "refinement": RefinementLoopAgent,
    "refinement_loop": RefinementLoopAgent,
    "iterative_refinement": RefinementLoopAgent,
    "complex_refinement": ComplexRefinementLoopAgent,
    "pipeline": ComplexRefinementLoopAgent,
    "pipeline_refinement": ComplexRefinementLoopAgent,
}

class ReasoningInterceptor:
    """
    A drop-in replacement for a standard Ollama client object.
    It intercepts 'generate' and 'chat' calls, checks for reasoning strategies 
    in the model name (e.g. 'gemma+cot'), and routes to the appropriate Agent.
    """
    def __init__(self, host="http://localhost:11434"):
        self.host = host

    def generate(self, model, prompt, system=None, stream=False, **kwargs):
        """
        Mimics ollama.generate signature.
        """
        # 1. Parse Strategy
        base_model = model
        strategy = "standard"
        
        if "+" in model:
            base_model, strategy_tag = model.split("+", 1)
            strategy = strategy_tag.lower().strip()
        
        if strategy not in AGENT_MAP:
            logger.warning(f"Unknown strategy '{strategy}', falling back to standard.")
            strategy = "standard"

        # 2. Instantiate Agent
        agent_class = AGENT_MAP[strategy]
        agent = agent_class(model=base_model)
        
        # 3. Execution
        # If stream=True, return a generator
        if stream:
            return self._stream_generator(agent, prompt)
        else:
            # Accumulate result
            full_response = ""
            for chunk in agent.stream(prompt):
                full_response += chunk
            
            return {
                "model": model,
                "response": full_response,
                "done": True
            }

    def chat(self, model, messages, stream=False, **kwargs):
        """
        Mimics ollama.chat signature.
        Converst messages list to a single prompt string for the Agents.
        """
        # Simple conversation flattener
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.upper()}: {content}\n"
        prompt += "ASSISTANT: "
        
        # Reuse generate logic
        return self.generate(model=model, prompt=prompt, stream=stream, **kwargs)

    def _stream_generator(self, agent, prompt):
        for chunk in agent.stream(prompt):
            yield {
                "model": agent.name, # Meta info
                "response": chunk,
                "done": False
            }
        yield {"done": True, "response": ""}

# Usage alias to look like the module
class Client(ReasoningInterceptor):
    pass
