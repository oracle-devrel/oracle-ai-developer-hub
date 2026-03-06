import re
from src.agents.base import BaseAgent
from src.visualization.models import StreamEvent, TaskStatus
from termcolor import colored
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class PipelineStage:
    """A single stage in the refinement pipeline."""
    name: str
    description: str
    critic_prompt_template: str
    refiner_prompt_template: str
    iteration: int = 0
    score: float = 0.0
    is_complete: bool = False
    feedback: str = ""


@dataclass
class PipelineIteration:
    """Tracks the current state of the pipeline refinement."""
    stage_index: int
    stage_name: str
    iteration_in_stage: int
    draft: str = ""
    critique: Optional[str] = None
    feedback: Optional[str] = None
    score: float = 0.0
    is_stage_complete: bool = False
    is_pipeline_complete: bool = False


# Define the 5 pipeline stages
PIPELINE_STAGES = [
    PipelineStage(
        name="Technical Accuracy",
        description="Ensure all facts, concepts, and technical details are correct",
        critic_prompt_template="""You are a technical accuracy reviewer. Evaluate the following article for TECHNICAL ACCURACY ONLY.

Question/Topic: {query}

Article to evaluate:
{draft}

Instructions:
1. Check all technical facts, formulas, and concepts for correctness.
2. Identify any inaccuracies, misconceptions, or misleading statements.
3. Provide a score from 0.0 to 1.0 based on technical accuracy.
4. If score < 0.9, provide specific corrections needed.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific technical corrections needed, or "Technically accurate" if score >= 0.9]""",
        refiner_prompt_template="""You are a technical editor. Fix the technical accuracy issues in the following article.

Original Topic: {query}

Current Article:
{draft}

Technical Accuracy Feedback:
{feedback}

Instructions: Rewrite the article fixing ALL technical inaccuracies mentioned. Keep the same structure and style, only fix the technical errors.

Corrected Article:"""
    ),
    PipelineStage(
        name="Structure & Clarity",
        description="Improve organization, logical flow, and readability",
        critic_prompt_template="""You are a structure and clarity reviewer. Evaluate the following article for STRUCTURE AND CLARITY ONLY.

Question/Topic: {query}

Article to evaluate:
{draft}

Instructions:
1. Assess the logical organization and flow of ideas.
2. Check if concepts are introduced in the right order.
3. Evaluate paragraph structure and transitions.
4. Provide a score from 0.0 to 1.0 based on structure and clarity.
5. If score < 0.9, provide specific structural improvements needed.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific structural improvements needed, or "Well structured" if score >= 0.9]""",
        refiner_prompt_template="""You are a structural editor. Improve the structure and clarity of the following article.

Original Topic: {query}

Current Article:
{draft}

Structure & Clarity Feedback:
{feedback}

Instructions: Reorganize and rewrite the article to address ALL structural issues mentioned. Improve flow, transitions, and logical ordering. Keep the technical content accurate.

Restructured Article:"""
    ),
    PipelineStage(
        name="Technical Depth",
        description="Add more technical details, formulas, and specifics",
        critic_prompt_template="""You are a technical depth reviewer. Evaluate the following article for TECHNICAL DEPTH ONLY.

Question/Topic: {query}

Article to evaluate:
{draft}

Instructions:
1. Assess whether the article has sufficient technical depth.
2. Check for missing important details, formulas, or algorithms.
3. Evaluate if explanations go deep enough for a technical audience.
4. Provide a score from 0.0 to 1.0 based on technical depth.
5. If score < 0.9, specify what technical details should be added.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific technical details to add, or "Sufficiently detailed" if score >= 0.9]""",
        refiner_prompt_template="""You are a technical writer. Enhance the technical depth of the following article.

Original Topic: {query}

Current Article:
{draft}

Technical Depth Feedback:
{feedback}

Instructions: Expand the article to add ALL the technical details mentioned in the feedback. Add formulas, algorithms, or specific details where needed. Maintain accuracy and structure.

Enhanced Article:"""
    ),
    PipelineStage(
        name="Examples & Analogies",
        description="Add concrete examples and helpful analogies",
        critic_prompt_template="""You are an examples and analogies reviewer. Evaluate the following article for EXAMPLES AND ANALOGIES ONLY.

Question/Topic: {query}

Article to evaluate:
{draft}

Instructions:
1. Assess whether the article has enough concrete examples.
2. Check if complex concepts have helpful analogies.
3. Evaluate if examples are relevant and illuminating.
4. Provide a score from 0.0 to 1.0 based on examples and analogies.
5. If score < 0.9, specify where examples or analogies should be added.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific examples/analogies to add, or "Well illustrated" if score >= 0.9]""",
        refiner_prompt_template="""You are a technical communicator. Add examples and analogies to the following article.

Original Topic: {query}

Current Article:
{draft}

Examples & Analogies Feedback:
{feedback}

Instructions: Add concrete examples and helpful analogies as specified in the feedback. Make abstract concepts more tangible. Maintain technical accuracy and structure.

Illustrated Article:"""
    ),
    PipelineStage(
        name="Professional Polish",
        description="Final editing for tone, flow, and professional presentation",
        critic_prompt_template="""You are a professional editor. Evaluate the following article for PROFESSIONAL POLISH ONLY.

Question/Topic: {query}

Article to evaluate:
{draft}

Instructions:
1. Assess the professional tone and voice.
2. Check for awkward phrasing, repetition, or verbosity.
3. Evaluate the overall polish and readability.
4. Provide a score from 0.0 to 1.0 based on professional polish.
5. If score < 0.9, specify what needs polishing.

Format your response EXACTLY as:
SCORE: [number between 0.0 and 1.0]
FEEDBACK: [specific polish improvements needed, or "Publication ready" if score >= 0.9]""",
        refiner_prompt_template="""You are a professional editor. Polish the following article for publication.

Original Topic: {query}

Current Article:
{draft}

Polish Feedback:
{feedback}

Instructions: Apply final polish to address ALL issues mentioned. Improve word choice, eliminate redundancy, and ensure professional tone. This is the final pass.

Polished Article:"""
    ),
]


class ComplexRefinementLoopAgent(BaseAgent):
    """
    Complex Refinement Pipeline Agent with 5 optimization stages.

    Implements a multi-stage pipeline:
    1. Technical Accuracy - ensure facts are correct
    2. Structure & Clarity - improve organization
    3. Technical Depth - add more details
    4. Examples & Analogies - add illustrations
    5. Professional Polish - final editing

    Each stage loops until score >= threshold before proceeding to next stage.
    """

    def __init__(self, model="gemma3:270m", score_threshold=0.9, max_iterations_per_stage=3):
        super().__init__(model)
        self.name = "ComplexRefinementLoopAgent"
        self.color = "magenta"
        self.score_threshold = score_threshold
        self.max_iterations_per_stage = max_iterations_per_stage
        self.stages = [PipelineStage(**{k: v for k, v in stage.__dict__.items()}) for stage in PIPELINE_STAGES]

    def run(self, query):
        self.log_thought(f"Processing query with Complex Refinement Pipeline: {query}")
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
            elif event.event_type == "pipeline":
                iteration = event.data
                if iteration.is_stage_complete:
                    yield colored(f"\n[✓ Stage '{iteration.stage_name}' COMPLETE - Score: {iteration.score:.2f}]\n", "green")
                if iteration.is_pipeline_complete:
                    yield colored(f"\n[✓ PIPELINE COMPLETE - All 5 stages passed!]\n", "green", attrs=["bold"])

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="phase", data="init")
        yield StreamEvent(event_type="text", data=f"Processing via Complex Refinement Pipeline (5 stages, threshold={self.score_threshold})...\n")

        # Display pipeline overview
        yield StreamEvent(event_type="text", data="\n" + "="*60 + "\n")
        yield StreamEvent(event_type="text", data="PIPELINE STAGES:\n")
        for i, stage in enumerate(self.stages, 1):
            yield StreamEvent(event_type="text", data=f"  {i}. {stage.name}: {stage.description}\n")
        yield StreamEvent(event_type="text", data="="*60 + "\n\n")

        # 1. GENERATE: Initial draft
        yield StreamEvent(event_type="phase", data="generating")
        yield StreamEvent(event_type="text", data="[GENERATOR] Creating initial draft...\n")

        generator_prompt = f"""You are a helpful assistant. Answer the following question thoroughly and accurately.

Question: {query}

Provide a comprehensive answer suitable for a technical blog:"""

        draft = ""
        yield StreamEvent(event_type="text", data="Initial Draft:\n")
        for chunk in self.client.generate(generator_prompt):
            draft += chunk
            yield StreamEvent(event_type="text", data=chunk)
        yield StreamEvent(event_type="text", data="\n")

        current_draft = draft

        # 2. PIPELINE: Process through each stage
        for stage_idx, stage in enumerate(self.stages):
            yield StreamEvent(event_type="text", data=f"\n{'='*60}\n")
            yield StreamEvent(event_type="text", data=f"[STAGE {stage_idx + 1}/5] {stage.name.upper()}\n")
            yield StreamEvent(event_type="text", data=f"Goal: {stage.description}\n")
            yield StreamEvent(event_type="text", data=f"{'='*60}\n")

            stage_complete = False
            iteration_in_stage = 0

            while not stage_complete and iteration_in_stage < self.max_iterations_per_stage:
                iteration_in_stage += 1

                # CRITIQUE for this stage
                yield StreamEvent(event_type="phase", data="critiquing")
                yield StreamEvent(event_type="text", data=f"\n[CRITIC - {stage.name}] Iteration {iteration_in_stage}/{self.max_iterations_per_stage}...\n")

                critic_prompt = stage.critic_prompt_template.format(query=query, draft=current_draft)

                critique_response = ""
                yield StreamEvent(event_type="text", data="Critique: ")
                for chunk in self.client.generate(critic_prompt):
                    critique_response += chunk
                    yield StreamEvent(event_type="text", data=chunk)
                yield StreamEvent(event_type="text", data="\n")

                # Parse score and feedback
                score = self._extract_score(critique_response)
                feedback = self._extract_feedback(critique_response)

                pipeline_iter = PipelineIteration(
                    stage_index=stage_idx,
                    stage_name=stage.name,
                    iteration_in_stage=iteration_in_stage,
                    draft=current_draft,
                    critique=critique_response,
                    feedback=feedback,
                    score=score
                )

                yield StreamEvent(event_type="text", data=f"\n   -> Score: {score:.2f}, Threshold: {self.score_threshold}\n")

                # Check if stage passes
                if score >= self.score_threshold:
                    stage_complete = True
                    pipeline_iter.is_stage_complete = True
                    stage.is_complete = True
                    stage.score = score

                    if stage_idx == len(self.stages) - 1:
                        pipeline_iter.is_pipeline_complete = True

                    yield StreamEvent(event_type="pipeline", data=pipeline_iter)
                    yield StreamEvent(event_type="text", data=colored(
                        f"\n[✓ STAGE PASSED] {stage.name} complete with score {score:.2f}\n", "green"
                    ))
                    break

                yield StreamEvent(event_type="pipeline", data=pipeline_iter)

                # REFINE for this stage
                yield StreamEvent(event_type="phase", data="refining")
                yield StreamEvent(event_type="text", data=f"\n[REFINER - {stage.name}] Improving based on feedback...\n")

                refiner_prompt = stage.refiner_prompt_template.format(
                    query=query,
                    draft=current_draft,
                    feedback=feedback
                )

                new_draft = ""
                yield StreamEvent(event_type="text", data="Refined Draft:\n")
                for chunk in self.client.generate(refiner_prompt):
                    new_draft += chunk
                    yield StreamEvent(event_type="text", data=chunk)
                yield StreamEvent(event_type="text", data="\n")

                current_draft = new_draft

            if not stage_complete:
                yield StreamEvent(event_type="text", data=colored(
                    f"\n[MAX ITERATIONS] Stage '{stage.name}' reached {self.max_iterations_per_stage} iterations. Moving to next stage.\n", "yellow"
                ))
                stage.is_complete = True  # Mark complete to proceed

        # 3. FINAL OUTPUT
        yield StreamEvent(event_type="phase", data="complete")
        yield StreamEvent(event_type="text", data="\n" + "="*60 + "\n")
        yield StreamEvent(event_type="text", data="PIPELINE SUMMARY:\n")
        for i, stage in enumerate(self.stages, 1):
            status = "✓" if stage.is_complete else "○"
            yield StreamEvent(event_type="text", data=f"  {status} Stage {i}: {stage.name} (score: {stage.score:.2f})\n")
        yield StreamEvent(event_type="text", data="="*60 + "\n")

        yield StreamEvent(event_type="text", data="\nFINAL RESULT:\n")
        yield StreamEvent(event_type="text", data=current_draft)
        yield StreamEvent(event_type="text", data="\n")

        yield StreamEvent(event_type="final", data=current_draft)

    def _extract_score(self, critique: str) -> float:
        """Extract numeric score from critique response."""
        match = re.search(r"SCORE:\s*(0?\.\d+|1\.0|1|0)", critique, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        match = re.search(r"\b(0\.\d+|1\.0)\b", critique)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return 0.5

    def _extract_feedback(self, critique: str) -> str:
        """Extract feedback from critique response."""
        match = re.search(r"FEEDBACK:\s*(.+)", critique, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return critique
