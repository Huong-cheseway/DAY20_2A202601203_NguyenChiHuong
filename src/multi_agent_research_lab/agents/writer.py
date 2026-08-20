"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        if not state.sources:
            state.errors.append("WriterAgent: cannot write without sources")
            state.add_trace_event("writer.skipped", {"reason": "missing sources"})
            return state

        context_notes = (
            state.analysis_notes
            or state.research_notes
            or "No intermediate notes available."
        )
        citations = []
        for idx, doc in enumerate(state.sources, start=1):
            doc_id = str(doc.metadata.get("document_id", idx))
            url = doc.url or "offline-source"
            citations.append(f"[{doc_id}] {doc.title} ({url})")

        final_answer = (
            f"Audience: {state.request.audience}\n\n"
            f"Query: {state.request.query}\n\n"
            "Synthesis:\n"
            "A multi-agent design is strongest when each role contributes a distinct artifact: "
            "research retrieval, reliability analysis, and final synthesis. "
            "In this run, the evidence suggests quality gains are conditional "
            "and should be weighed against coordination overhead.\n\n"
            "Analysis notes:\n"
            f"{context_notes}\n\n"
            "Citations:\n"
            + "\n".join(citations)
        )

        state.final_answer = final_answer
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=final_answer,
                metadata={"num_citations": len(citations)},
            )
        )
        state.add_trace_event("writer.done", {"num_citations": len(citations)})
        return state
