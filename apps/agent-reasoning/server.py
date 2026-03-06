import json
import asyncio
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import unified AGENT_MAP from interceptor (single source of truth)
from src.interceptor import AGENT_MAP

app = FastAPI(title="Agent Reasoning Gateway")

class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True
    # Other ollama fields ignored for this demo

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    # 1. Parse Model String to find Strategy
    # Format: "model_name+strategy" e.g. "gemma3+cot"
    if "+" in request.model:
        base_model, strategy = request.model.split("+", 1)
    else:
        base_model = request.model
        strategy = "standard" # Default
    
    strategy = strategy.lower().strip()
    
    if strategy not in AGENT_MAP:
        # Fallback to standard if unknown strategy
        strategy = "standard"
        
    print(f"Rx Request: Model={base_model}, Strategy={strategy}")

    # 2. Instantiate Agent
    agent_class = AGENT_MAP[strategy]
    # We pass the base model requested by user to the agent
    agent = agent_class(model=base_model)
    
    # 3. Stream Response with timing
    async def response_generator():
        start_time = time.time()
        first_token_time = None
        chunk_count = 0
        try:
            for chunk in agent.stream(request.prompt):
                if first_token_time is None:
                    first_token_time = time.time()
                chunk_count += 1
                data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": chunk,
                    "done": False
                }
                yield json.dumps(data) + "\n"
                await asyncio.sleep(0)

            end_time = time.time()
            total_duration = int((end_time - start_time) * 1e9)
            ttft_ns = int((first_token_time - start_time) * 1e9) if first_token_time else 0

            data = {
                    "model": request.model,
                    "created_at": "2023-01-01T00:00:00.000000Z",
                    "response": "",
                    "done": True,
                    "total_duration": total_duration,
                    "load_duration": ttft_ns,
                    "prompt_eval_count": 0,
                    "eval_count": chunk_count
            }
            yield json.dumps(data) + "\n"
        except Exception as e:
            err_data = {
                "response": f"\n\n[Error in Reasoning Agent: {str(e)}]",
                "done": True
            }
            yield json.dumps(err_data) + "\n"

    return StreamingResponse(response_generator(), media_type="application/x-ndjson")


# Agent descriptions for API consumers
AGENT_INFO = {
    "standard": {"name": "Standard", "description": "Direct generation without reasoning enhancement", "ref": "N/A"},
    "cot": {"name": "Chain of Thought", "description": "Step-by-step reasoning decomposition", "ref": "Wei et al. (2022)"},
    "tot": {"name": "Tree of Thoughts", "description": "Branching exploration with scoring and pruning", "ref": "Yao et al. (2023)"},
    "react": {"name": "ReAct", "description": "Interleaved reasoning and tool-use actions", "ref": "Yao et al. (2022)"},
    "recursive": {"name": "Recursive LM", "description": "Code-generation REPL with recursive LLM calls", "ref": "Author et al. (2025)"},
    "reflection": {"name": "Self-Reflection", "description": "Draft-critique-refine loop until correct", "ref": "Shinn et al. (2023)"},
    "consistency": {"name": "Self-Consistency", "description": "Multiple samples with majority voting", "ref": "Wang et al. (2022)"},
    "decomposed": {"name": "Decomposed Prompting", "description": "Break problem into sub-tasks, solve sequentially", "ref": "Khot et al. (2022)"},
    "least_to_most": {"name": "Least-to-Most", "description": "Solve from easiest sub-question to hardest", "ref": "Zhou et al. (2022)"},
    "refinement": {"name": "Refinement Loop", "description": "Iterative score-based generation and refinement", "ref": "Iterative Refinement"},
    "complex_refinement": {"name": "Complex Pipeline", "description": "5-stage refinement pipeline with specialized critics", "ref": "Multi-Stage Refinement"},
}


@app.get("/api/tags")
async def tags():
    """Return available model+strategy combinations (Ollama-compatible)."""
    strategies = sorted(set(
        k for k in AGENT_MAP.keys()
        if k in AGENT_INFO  # Only primary names, not aliases
    ))
    return {
        "models": [{"name": f"gemma3:270m+{s}"} for s in strategies]
    }


@app.get("/api/agents")
async def list_agents():
    """List available reasoning agents with descriptions."""
    agents = []
    for strategy_id, info in AGENT_INFO.items():
        agents.append({
            "id": strategy_id,
            "name": info["name"],
            "description": info["description"],
            "reference": info["ref"],
            "has_visualizer": strategy_id in ("cot", "tot", "react", "consistency", "decomposed", "least_to_most", "reflection", "refinement"),
        })
    return {"agents": agents, "count": len(agents)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
