"""Optional deterministic critic for citation and completion checks."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final-answer presence and citation coverage."""

        if not state.final_answer:
            state.errors.append("CriticAgent: final answer is missing")
            state.add_trace_event("critic.failed", {"reason": "missing final answer"})
            return state

        answer = state.final_answer.lower()
        missing = [
            str(doc.metadata.get("document_id", "unknown"))
            for doc in state.sources
            if f"[{str(doc.metadata.get('document_id', 'unknown')).lower()}]" not in answer
        ]
        coverage = (
            1.0 if not state.sources else (len(state.sources) - len(missing)) / len(state.sources)
        )
        findings = f"Citation coverage: {coverage:.0%}. " + (
            f"Missing source IDs: {', '.join(missing)}." if missing else "All source IDs cited."
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=findings,
                metadata={"citation_coverage": coverage, "missing_source_ids": missing},
            )
        )
        state.add_trace_event(
            "critic.done", {"citation_coverage": coverage, "missing_source_ids": missing}
        )
        return state
