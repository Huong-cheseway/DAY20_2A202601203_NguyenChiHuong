"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        docs = self.search_client.search(state.request.query, max_results=state.request.max_sources)
        if not docs:
            state.errors.append("ResearcherAgent: no sources found")
            state.add_trace_event("researcher.empty", {"query": state.request.query})
            return state

        state.sources = docs
        state.research_notes = "\n".join(
            f"[{doc.metadata.get('document_id', idx + 1)}] {doc.title}: {doc.snippet}"
            for idx, doc in enumerate(docs)
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={"num_sources": len(docs)},
            )
        )
        state.add_trace_event(
            "researcher.done",
            {
                "num_sources": len(docs),
                "topic": docs[0].metadata.get("topic_name") if docs else None,
            },
        )
        return state
