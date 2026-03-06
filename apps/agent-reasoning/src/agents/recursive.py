import re
import sys
import io
from termcolor import colored
from src.agents.base import BaseAgent

class RecursiveAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "RecursiveAgent"
        self.color = "cyan"

    def _sub_llm(self, prompt):
        """
        Helper function exposed to the REPL.
        Allows the agent to call the LLM recursively on data.
        """
        response = ""
        # We use a new client call effectively (or reuse the existing one's method)
        # Note: We need to avoid infinite recursion loops on the INTERCEPTOR level
        # if the prompt triggers another agent.
        # But here we are calling self.client.generate which goes to Ollama directly (Client class in client.py),
        # UNLESS self.client is the Interceptor?
        # In base.py: self.client = OllamaClient(model=model)
        # OllamaClient (src/client.py) talks to HTTP API directly.
        # So this is safe from interceptor recursion logic, it acts as a "base" LLM call.
        # However, it uses the SAME model as the agent.
        
        for chunk in self.client.generate(prompt, stream=True):
            response += chunk
        return response

    def run(self, query):
        self.log_thought(f"Processing query with RecursiveAgent")
        full_res = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_res += chunk
        print()
        return full_res

    def stream(self, query):
        self.log_thought(f"Initializing Recursive Context.")
        
        # 1. Setup Environment
        # We assume the query IS the INPUT.
        env = {
            "INPUT": query,
            "sub_llm": self._sub_llm,
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "list": list,
            "dict": dict,
            "set": set,
            "min": min,
            "max": max,
            "sum": sum,
            "sorted": sorted,
            "enumerate": enumerate,
            # Add other safe builtins as needed
        }
        
        system_prompt = """You are a Recursive Language Model (RLM).
You have access to a Python execution environment (REPL).
The user's input is stored in `INPUT`.
Your goal: Write Python code to solve the user's problem.

CRITICAL INSTRUCTIONS:
1. You MUST start your response with a "Thought:", followed by a python code block: ```python ... ```.
2. The code block MUST assign the final result to `FINAL_ANSWER`.
3. Use `print()` to debug or see values.
4. `sub_llm(prompt)` is available to ask the LLM questions about data.
5. DO NOT COPY THE EXAMPLE. Write NEW code to solve the `INPUT`.

Example:
Thought: I need to process the data.
```python
# checking input
print(INPUT[:50])
# ... my logic ...
result = "done"
FINAL_ANSWER = result
```
"""

        messages = f"{system_prompt}\n"
        history = "" 
        
        max_steps = 8
        
        for step in range(max_steps):
            # Construct prompt for this step
            # We treat the history as part of the prompt context
            preview = env["INPUT"][:200]
            current_prompt = f"{messages}\nHistory of execution:\n{history}\n\nExisting Variables: {list(env.keys())}\n(Input Preview: {preview}...)\n\nNext Step (Thought + Code):"
            
            yield f"\n\n--- Step {step+1} ---\nAgent: "
            
            # Stream the thought/code generation
            step_response = ""
            # We yield chunks to the user
            # Stop at "Observation:" locally if the model hallucinates it?
            # But the model might write code then "Observation" comes from US.
            # So stopping at ```output``` or similar might be good, but let's just parse.
            
            for chunk in self.client.generate(current_prompt, stream=True, stop=["Observation:"]):
                 yield chunk
                 step_response += chunk
            
            # Parse code
            code_match = re.search(r"```python(.*?)```", step_response, re.DOTALL)
            if not code_match:
                code_match = re.search(r"```(.*?)```", step_response, re.DOTALL)
                
            if code_match:
                code = code_match.group(1).strip()
                if "python" in code.lower() and len(code) < 10: # Handle ```python\n code``` edge case parsing
                     pass # rudimentary check
                
                yield colored(f"\nExecuting Code...", "yellow")
                
                # Execute
                output_buffer = io.StringIO()
                original_stdout = sys.stdout
                sys.stdout = output_buffer
                
                execution_error = None
                try:
                    exec(code, env)
                    result = output_buffer.getvalue()
                except Exception as e:
                    execution_error = e
                    result = f"Error: {e}"
                finally:
                    sys.stdout = original_stdout
                    
                obs_str = f"\nObservation:\n{result}\n"
                yield colored(obs_str, "blue")
                
                history += f"Step {step+1}:\n{step_response}\n{obs_str}\n"
                
                if "FINAL_ANSWER" in env:
                    yield colored(f"\nFINAL ANSWER FOUND\n", "green")
                    final_ans = str(env["FINAL_ANSWER"])
                    yield final_ans
                    # Break the generator
                    return
            else:
                yield colored("\nNo code block found. Ending turn.\n", "red")
                # Append to history, maybe it's just thinking?
                history += f"Step {step+1}: {step_response}\n"
                
                if "FINAL_ANSWER" in step_response: # Fallback if it just hallucinates "FINAL_ANSWER = ..." without code?
                     # But we told it to assign to var.
                     pass

        yield colored("\nMax steps reached without FINAL_ANSWER.\n", "red")
