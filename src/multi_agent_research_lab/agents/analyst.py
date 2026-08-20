"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        if not state.sources:
            state.errors.append("AnalystAgent: no sources to analyze")
            state.add_trace_event("analyst.skipped", {"reason": "missing sources"})
            return state

        public_count = 0
        synthetic_count = 0
        reliability_lines: list[str] = []
        for doc in state.sources:
            doc_id = str(doc.metadata.get("document_id", "unknown"))
            is_synthetic = bool(doc.metadata.get("is_synthetic", False))
            doc_class = str(doc.metadata.get("document_class", "unknown"))
            if is_synthetic:
                synthetic_count += 1
            else:
                public_count += 1

            if is_synthetic and "survey" in doc_class:
                reliability = "lower confidence (synthetic opinion evidence)"
            elif is_synthetic:
                reliability = "medium confidence (synthetic benchmark evidence)"
            elif "public_reference_summary" in doc_class:
                reliability = "high confidence for scoped architectural claims"
            else:
                reliability = "medium confidence"
            reliability_lines.append(f"- [{doc_id}] {doc.title}: {reliability}")

        analysis = (
            "Comparison:\n"
            f"- Public references: {public_count}\n"
            f"- Synthetic benchmark sources: {synthetic_count}\n"
            "- Public references provide architecture/evaluation anchors; "
            "synthetic sources are useful for controlled trade-off analysis "
            "but should be labeled as synthetic.\n\n"
            "Source reliability assessment:\n"
            + "\n".join(reliability_lines)
            + "\n\n"
            "Synthesis guidance:\n"
            "- Prefer claims supported by multiple source types.\n"
            "- Treat cost/latency improvements as conditional on task complexity.\n"
            "- Mark synthetic evidence explicitly in final writing to avoid overclaiming."
        )
        estimated_tokens = max(1, len(analysis) // 4)

        state.analysis_notes = analysis
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=analysis,
                metadata={
                    "public_sources": public_count,
                    "synthetic_sources": synthetic_count,
                    "estimated_tokens": estimated_tokens,
                },
            )
        )
        state.add_trace_event(
            "analyst.done",
            {
                "public_sources": public_count,
                "synthetic_sources": synthetic_count,
                "estimated_tokens": estimated_tokens,
            },
        )
        return state
