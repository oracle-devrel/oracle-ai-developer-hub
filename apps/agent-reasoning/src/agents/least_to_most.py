from src.agents.base import BaseAgent
from termcolor import colored

class LeastToMostAgent(BaseAgent):
    def __init__(self, model="gemma3:270m"):
        super().__init__(model)
        self.name = "LeastToMostAgent"
        self.color = "cyan"

    def run(self, query):
        # Default run implementation accumulating stream
        response = ""
        for chunk in self.stream(query):
            response += chunk
        return response

    def stream(self, query):
        yield f"Processing query via Least-to-Most Prompting: {query}\n"

        # 1. Decomposition into sub-questions (easy to hard)
        yield "\n**Decomposing into sub-questions (easy -> hard)...**\n"
        decomp_prompt = f"To solve the question '{query}', list the sub-questions that need to be answered, starting from the easiest/foundational ones to the final question. Output as a numbered list."
        
        plan_text = ""
        for chunk in self.client.generate(decomp_prompt):
            plan_text += chunk
        yield f"**Plan:**\n{plan_text}\n"

        # 2. Sequential Solving
        sub_questions = [line.strip() for line in plan_text.split('\n') if line.strip()]
        history = ""

        for q in sub_questions:
            yield f"\n**Addressing:** `{q}`\n"
            prompt = f"Q: {q}\nAnswer this specific question based on prior context if applicable.\nContext:\n{history}"
            
            yield f"Answer: "
            answer = ""
            for chunk in self.client.generate(prompt):
                 yield chunk
                 answer += chunk
            yield "\n"
            
            history += f"Q: {q}\nA: {answer}\n"
