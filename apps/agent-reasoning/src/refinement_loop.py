import random
import time
from dataclasses import dataclass

@dataclass
class Critique:
    score: float
    feedback: str

class Generator:
    def invoke(self, query: str) -> str:
        """
        Generates an initial draft based on the query.
        In a real scenario, this would call an LLM.
        """
        print(f"  [Generator] Generating initial draft for: '{query}'")
        # Simulating a basic draft
        return f"Draft response to: {query}. Basic info included."

class Critic:
    def invoke(self, draft: str) -> Critique:
        """
        Critiques the draft and returns a score and feedback.
        In a real scenario, this would call an LLM to evaluate the draft.
        """
        # Simulating critique logic for a "Harder Task"
        # Start lower to simulate complexity
        score = 0.3
        
        # Heuristic: Slower progress for harder tasks
        # Each "refined" keyword adds only 0.08 points now (was 0.2)
        improvement_count = draft.count("refined")
        score += (improvement_count * 0.08)
        
        # Add some random variance to simulate non-linear progress
        score += random.uniform(-0.02, 0.03)
        
        # Cap score
        score = min(score, 0.95)
        
        feedback = "Critique: Explanation is too shallow. Expand on the recursive properties."
        if score > 0.6:
            feedback = "Critique: Better, but needs more formal definitions."
        if score > 0.8:
            feedback = "Critique: Good, just polish the conclusion."
        if score >= 0.9:
            feedback = "Excellent. Ready for publication."

        print(f"  [Critic] Score: {score:.2f} | Feedback: {feedback}")
        return Critique(score=score, feedback=feedback)

class Refiner:
    def invoke(self, draft: str, feedback: str) -> str:
        """
        Refines the draft based on the critic's feedback.
        """
        print(f"  [Refiner] Refining draft based on feedback...")
        # Simulating refinement
        return f"{draft} [refined with: {feedback}]"

def refinement_loop(query: str, threshold: float = 0.9, max_iterations: int = 5) -> str:
    """
    Orchestrates the refinement loop: Generator -> Critic -> Refiner -> Critic ...
    """
    generator = Generator()
    critic = Critic()
    refiner = Refiner()

    print(f"\n--- Starting Refinement Loop for: '{query}' ---\n")

    # 1. Initial Draft
    draft = generator.invoke(query)
    
    # 2. Initial Critique
    critique = critic.invoke(draft)
    
    iteration = 0
    while critique.score < threshold and iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        # 3. Refine
        draft = refiner.invoke(draft, critique.feedback)
        
        # 4. Critique again
        critique = critic.invoke(draft)
    
    if critique.score >= threshold:
        print(f"\n[Success] Threshold {threshold} met at iteration {iteration}!")
    else:
        print(f"\n[Stop] Max iterations ({max_iterations}) reached.")

    return draft
