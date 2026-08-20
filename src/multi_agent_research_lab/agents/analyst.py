"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient, LLMResponse


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

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

        fallback_analysis = (
            "Comparison:\n"
            f"- Public references: {public_count}\n"
            f"- Synthetic benchmark sources: {synthetic_count}\n"
            "- Public references provide architecture/evaluation anchors; "
            "synthetic sources are useful for controlled trade-off analysis "
            "but should be labeled as synthetic.\n\n"
            "Source reliability assessment:\n" + "\n".join(reliability_lines) + "\n\n"
            "Synthesis guidance:\n"
            "- Prefer claims supported by multiple source types.\n"
            "- Treat cost/latency improvements as conditional on task complexity.\n"
            "- Mark synthetic evidence explicitly in final writing to avoid overclaiming."
        )
        response: LLMResponse | None = None
        analysis = fallback_analysis
        fallback_used = True
        if self.llm_client.is_configured:
            evidence = "\n".join(
                f"[{doc.metadata.get('document_id', 'unknown')}] {doc.title}: {doc.snippet}"
                for doc in state.sources
            )
            try:
                response = self.llm_client.complete(
                    system_prompt=(
                        "You are the Analyst in a multi-agent research workflow. Analyze only "
                        "the supplied evidence. Compare viewpoints, assess source reliability, "
                        "identify uncertainty, and produce actionable synthesis guidance. "
                        "Keep document IDs in square brackets when referring to evidence."
                    ),
                    user_prompt=(
                        f"Research question:\n{state.request.query}\n\n"
                        f"Evidence:\n{evidence}\n\n"
                        "Return a concise structured analysis. Explicitly label synthetic evidence."
                    ),
                )
                if response.content.strip():
                    analysis = response.content.strip()
                    fallback_used = False
            except AgentExecutionError as exc:
                fallback_used = True
                state.add_trace_event(
                    "analyst.fallback",
                    {
                        "reason": type(exc).__name__,
                        "provider": self.llm_client.settings.llm_provider,
                    },
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
                    "input_tokens": response.input_tokens if response else None,
                    "output_tokens": response.output_tokens if response else None,
                    "cost_usd": response.cost_usd if response else 0.0,
                    "provider": response.provider if response else "local",
                    "model": response.model if response else None,
                    "fallback_used": fallback_used,
                },
            )
        )
        state.add_trace_event(
            "analyst.done",
            {
                "public_sources": public_count,
                "synthetic_sources": synthetic_count,
                "estimated_tokens": estimated_tokens,
                "input_tokens": response.input_tokens if response else None,
                "output_tokens": response.output_tokens if response else None,
                "cost_usd": response.cost_usd if response else 0.0,
                "provider": response.provider if response else "local",
                "model": response.model if response else None,
                "fallback_used": fallback_used,
            },
        )
        return state
