from abc import ABC, abstractmethod
from src.client import OllamaClient
from termcolor import colored

class BaseAgent(ABC):
    def __init__(self, model="gemma3:270m"):
        self.client = OllamaClient(model=model)
        self.name = "BaseAgent"
        self.color = "white"

    def log_thought(self, message):
        print(colored(f"[{self.name}]: {message}", self.color))

    @abstractmethod
    def run(self, query):
        pass

    def stream(self, query):
        """
        Default generator that yields chunks.
        Subclasses should implement this or run() to support streaming.
        If only run() is implemented, this wrapper yields the final result as one chunk.
        """
        result = self.run(query)
        if result:
            yield result
