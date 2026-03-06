import re
from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import StreamEvent, TaskStatus, RefinementIteration
from termcolor import colored


class RefinementLoopAgent(BaseAgent):
    """
    Iterative Refinement Agent with score-based termination.

    Implements the refinement loop pattern:
    1. Generator creates initial draft
    2. Critic evaluates with a score (0.0-1.0) and provides feedback
    3. Refiner improves draft based on feedback
    4. Loop until score >= threshold

    Reference: Based on iterative refinement patterns for reliable generation.
    """

    def __init__(self, model="gemma3:270m", score_threshold=0.9, max_iterations=10):
        super().__init__(model)
        self.name = "RefinementLoopAgent"
        self.color = "yellow"
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations

    def run(self, query):
        self.log_thought(f"Processing query with Refinement Loop: {query}")
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        """Legacy text streaming for backward compatibility."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data
            elif event.event_type == "refinement":
                iteration = event.data
                if iteration.is_accepted:
                    yield colored(f"\n[Score {iteration.score:.2f} >= {self.score_threshold} - ACCEPTED]\n", "green")

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data=f"Processing via Refinement Loop (threshold={self.score_threshold})...\n")

        # 1. GENERATE: Initial draft
        yield StreamEvent(event_type="text", data="\n[GENERATOR] Creating initial draft...\n")

        generator_prompt = f"""You are a helpful assistant. Answer the following question thoroughly and accurately.

Question: {query}

Provide a comprehensive answer:"""

        draft = ""
        iteration = RefinementIteration(iteration=1, draft="")
        yield StreamEvent(event_type="refinement", data=iteration)

        yield StreamEvent(event_type="text", data="Draft: ")
        for chunk in self.client.generate(generator_prompt):
            draft += chunk
            iteration.draft = draft
            yield StreamEvent(event_type="refinement", data=iteration, is_update=True)
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n")

        # 2. CRITIQUE & REFINE Loop
        current_draft = draft

        for i in range(self.max_iterations):
            yield StreamEvent(event_type="text", data=f"\n[CRITIC] Evaluating draft (iteration {i+1}/{self.max_iterations})...\n")

            # Critic evaluates and provides score + feedback
            critic_prompt = f"""You are a strict quality evaluator. Evaluate the following answer to the question.

Question: {query}

Answer to evaluate:
{current_draft}

Instructions:
1. Assess the answer for accuracy, completeness, clarity, and relevance.
2. Provide a quality score from 0.0 to 1.0 (where 1.0 is perfect).
3. If the score is below 0.9, provide specific feedback on what needs improvement.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific improvement suggestions, or "No improvements needed" if score >= 0.9]"""

            critique_response = ""
            yield StreamEvent(event_type="text", data="Critique: ")
            for chunk in self.client.generate(critic_prompt):
                critique_response += chunk
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            # Parse score and feedback
            score = self._extract_score(critique_response)
            feedback = self._extract_feedback(critique_response)

            iteration = RefinementIteration(
                iteration=i + 1,
                draft=current_draft,
                critique=critique_response,
                feedback=feedback,
                score=score
            )

            yield StreamEvent(event_type="text", data=f"\n   -> Score: {score:.2f}, Threshold: {self.score_threshold}\n")

            # Check if we've reached the threshold
            if score >= self.score_threshold:
                iteration.is_accepted = True
                yield StreamEvent(event_type="refinement", data=iteration)
                yield StreamEvent(event_type="text", data=colored(f"\n[ACCEPTED] Score {score:.2f} meets threshold.\n", "green"))
                break

            yield StreamEvent(event_type="refinement", data=iteration)

            # 3. REFINE: Improve draft based on feedback
            yield StreamEvent(event_type="text", data=f"\n[REFINER] Improving draft based on feedback...\n")

            refiner_prompt = f"""You are a skilled editor. Improve the following answer based on the feedback provided.

Original Question: {query}

Current Draft:
{current_draft}

Feedback to address:
{feedback}

Instructions: Rewrite the answer to address ALL the feedback points. Maintain accuracy while improving quality.

Improved Answer:"""

            new_draft = ""
            yield StreamEvent(event_type="text", data="Refined Draft: ")
            for chunk in self.client.generate(refiner_prompt):
                new_draft += chunk
                yield StreamEvent(event_type="text", data=chunk)
            yield StreamEvent(event_type="text", data="\n")

            current_draft = new_draft

        else:
            # Max iterations reached without meeting threshold
            yield StreamEvent(event_type="text", data=colored(
                f"\n[MAX ITERATIONS] Reached {self.max_iterations} iterations. Using best draft.\n", "yellow"
            ))

        yield StreamEvent(event_type="text", data="\n" + "="*50 + "\n")
        yield StreamEvent(event_type="text", data="FINAL RESULT:\n")
        yield StreamEvent(event_type="text", data=current_draft)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=current_draft)

    def _extract_score(self, critique: str) -> float:
        """Extract numeric score from critique response."""
        # Try to find "SCORE: X.X" pattern
        match = re.search(r"SCORE:\s*(0?\.\d+|1\.0|1|0)", critique, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Fallback: look for any decimal number
        match = re.search(r"\b(0\.\d+|1\.0)\b", critique)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        # Default to low score if parsing fails
        return 0.5

    def _extract_feedback(self, critique: str) -> str:
        """Extract feedback from critique response."""
        # Try to find "FEEDBACK: ..." pattern
        match = re.search(r"FEEDBACK:\s*(.+)", critique, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

        # Fallback: return entire critique as feedback
        return critique
