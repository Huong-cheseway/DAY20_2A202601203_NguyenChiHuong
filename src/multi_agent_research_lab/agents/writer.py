"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient, LLMResponse


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        if not state.sources:
            state.errors.append("WriterAgent: cannot write without sources")
            state.add_trace_event("writer.skipped", {"reason": "missing sources"})
            return state

        context_notes = (
            state.analysis_notes or state.research_notes or "No intermediate notes available."
        )
        citations = []
        for idx, doc in enumerate(state.sources, start=1):
            doc_id = str(doc.metadata.get("document_id", idx))
            url = doc.url or "offline-source"
            citations.append(f"[{doc_id}] {doc.title} ({url})")

        fallback_body = (
            f"Audience: {state.request.audience}\n\n"
            f"Query: {state.request.query}\n\n"
            "Synthesis:\n"
            f"{context_notes}"
        )
        response: LLMResponse | None = None
        answer_body = fallback_body
        fallback_used = True
        if self.llm_client.is_configured:
            evidence = "\n".join(
                f"[{doc.metadata.get('document_id', idx)}] {doc.title}: {doc.snippet}"
                for idx, doc in enumerate(state.sources, start=1)
            )
            try:
                response = self.llm_client.complete(
                    system_prompt=(
                        "You are the Writer in a multi-agent research workflow. Answer the exact "
                        "research question for the requested audience using only the supplied "
                        "analysis and evidence. Make the answer specific, explain uncertainty, "
                        "and cite factual claims with document IDs such as [source-id]. Do not "
                        "invent sources or URLs."
                    ),
                    user_prompt=(
                        f"Question:\n{state.request.query}\n\n"
                        f"Audience:\n{state.request.audience}\n\n"
                        f"Analysis:\n{context_notes}\n\n"
                        f"Evidence:\n{evidence}\n\n"
                        "Write the final answer. Do not add a bibliography; it will be appended."
                    ),
                )
                if response.content.strip():
                    answer_body = response.content.strip()
                    fallback_used = False
            except AgentExecutionError as exc:
                fallback_used = True
                state.add_trace_event(
                    "writer.fallback",
                    {
                        "reason": type(exc).__name__,
                        "provider": self.llm_client.settings.llm_provider,
                    },
                )

        final_answer = f"{answer_body}\n\nCitations:\n" + "\n".join(citations)
        estimated_tokens = max(1, len(final_answer) // 4)

        state.final_answer = final_answer
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=final_answer,
                metadata={
                    "num_citations": len(citations),
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
            "writer.done",
            {
                "num_citations": len(citations),
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
