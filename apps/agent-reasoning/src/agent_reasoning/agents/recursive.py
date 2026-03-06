import re
import sys
import io
from termcolor import colored
from agent_reasoning.agents.base import BaseAgent

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
        
        system_prompt = """You are a Python coding assistant that solves problems step by step.

RULES:
1. Write Python code in ```python ... ``` blocks
2. Use the variable INPUT which contains the user's question
3. Use sub_llm(prompt) to ask the LLM for text answers
4. Set FINAL_ANSWER = "your answer" when done (REQUIRED!)

IMPORTANT: Always end by setting FINAL_ANSWER!

Example for math problems:
Thought: I need to calculate the math expression.
```python
# The question asks: What is 2 + 3 * 4?
# Following order of operations: 3 * 4 = 12, then 2 + 12 = 14
result = 2 + 3 * 4
print(f"The answer is {result}")
FINAL_ANSWER = f"The answer is {result}"
```

Example for text questions:
Thought: I need to get an answer from the LLM.
```python
answer = sub_llm(INPUT)
FINAL_ANSWER = answer
```
"""

        messages = f"{system_prompt}\n"
        history = "" 
        
        max_steps = 8
        
        for step in range(max_steps):
            # Construct prompt for this step
            full_input = env["INPUT"]
            if step == 0:
                current_prompt = f"""{messages}

USER'S QUESTION: {full_input}

Write Python code to answer this question. Set FINAL_ANSWER when done.

Thought:"""
            else:
                current_prompt = f"""{messages}

USER'S QUESTION: {full_input}

Previous steps:
{history}

Continue. Set FINAL_ANSWER when you have the answer.

Thought:"""
            
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
