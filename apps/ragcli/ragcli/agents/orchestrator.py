"""Agent orchestrator: coordinates Planner -> Researcher -> Reasoner -> Synthesizer."""

from typing import Dict, Any, Optional, Callable, List
from .planner import Planner
from .researcher import Researcher
from .reasoner import Reasoner
from .synthesizer import Synthesizer
from .trace import ReasoningTrace
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.planner = Planner(config)
        self.researcher = Researcher(config)
        self.reasoner = Reasoner(config)
        self.synthesizer = Synthesizer(config)

    def run(
        self,
        query: str,
        search_func: Optional[Callable] = None,
        session_context: str = "",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace = ReasoningTrace(query, session_id=session_id)

        try:
            # Step 1: Plan
            plan = self.planner.run(query, session_context)
            trace.add_step("planner", {"query": query}, plan, f"Decomposed into {len(plan['sub_queries'])} sub-queries")
            trace.finalize_step()

            # Step 2: Research each sub-query
            if search_func is None:
                search_func = lambda q: []

            all_evidence: List[Dict[str, Any]] = []
            for sq in plan["sub_queries"]:
                research_result = self.researcher.run(sq, search_func)
                all_evidence.extend(research_result["evidence"])

            trace.add_step("researcher", {"sub_queries": plan["sub_queries"]}, {"evidence_count": len(all_evidence)}, f"Found {len(all_evidence)} evidence chunks")
            trace.finalize_step()

            # Step 3: Reason
            reason_result = self.reasoner.run(query, all_evidence)
            trace.add_step("reasoner", {"evidence_count": len(all_evidence)}, reason_result, reason_result.get("analysis", "")[:500])
            trace.finalize_step()

            # Step 4: Synthesize
            synth_result = self.synthesizer.run(query, reason_result.get("analysis", ""), all_evidence)
            trace.add_step("synthesizer", {"analysis_length": len(reason_result.get("analysis", ""))}, synth_result, "")
            trace.finalize_step()

            return {
                "answer": synth_result.get("answer", ""),
                "confidence": synth_result.get("confidence", 0.0),
                "sources": synth_result.get("sources", []),
                "evidence": all_evidence,
                "trace_id": trace.trace_id,
                "trace": trace,
            }

        except Exception as e:
            logger.error(f"Orchestrator pipeline failed, falling back: {e}")
            return self._fallback(query, search_func, trace)

    def _fallback(self, query: str, search_func: Optional[Callable], trace: ReasoningTrace) -> Dict[str, Any]:
        """Fall back to simple search + synthesize."""
        evidence: List[Dict[str, Any]] = []
        if search_func:
            try:
                raw = search_func(query)
                evidence = [
                    {
                        "chunk_id": c.get("chunk_id", ""),
                        "text": c.get("text", ""),
                        "similarity_score": c.get("similarity_score", 0),
                        "document_id": c.get("document_id", ""),
                    }
                    for c in raw
                ]
            except Exception:
                pass

        context = "\n".join(e.get("text", "") for e in evidence)
        answer = context[:1000] if context else "I couldn't find relevant information to answer your question."

        trace.add_step("fallback", {"query": query}, {"evidence_count": len(evidence)}, "Pipeline failed, used direct search")
        trace.finalize_step()

        return {
            "answer": answer,
            "confidence": 0.0,
            "sources": [],
            "evidence": evidence,
            "trace_id": trace.trace_id,
            "trace": trace,
        }
