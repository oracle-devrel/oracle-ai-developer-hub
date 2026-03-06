from agent_reasoning.agents.base import BaseAgent
from termcolor import colored

class StandardAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "StandardAgent"
        self.color = "cyan"

    def run(self, query):
        # Keeps legacy run behavior (print to stdout)
        self.log_thought(f"Processing query: {query}")
        print(colored("Answer: ", self.color), end="", flush=True)
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print() 
        return full_response

    def stream(self, query):
        # Yields chunks directly from client
        # Wrap in basic instruction to ensure responsiveness
        prompt = f"Question: {query}\n\nAnswer:"
        for chunk in self.client.generate(prompt):
            yield chunk
