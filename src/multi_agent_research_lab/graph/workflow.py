"""LangGraph workflow for the multi-agent research pipeline."""

import asyncio
from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(
        self,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.supervisor = SupervisorAgent()
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent(llm_client=llm_client)
        self.writer = writer or WriterAgent(llm_client=llm_client)

    def build(self) -> Any:
        """Create a LangGraph graph."""

        settings = get_settings()
        worker_policy = RetryPolicy(max_attempts=settings.llm_max_retries + 1)
        worker_timeout = timedelta(seconds=settings.timeout_seconds)
        graph = StateGraph(ResearchState)
        graph.add_node("supervisor", self._run_supervisor)
        graph.add_node(
            "researcher",
            self._run_researcher,
            retry_policy=worker_policy,
            timeout=worker_timeout,
        )
        graph.add_node(
            "analyst",
            self._run_analyst,
            retry_policy=worker_policy,
            timeout=worker_timeout,
        )
        graph.add_node(
            "writer",
            self._run_writer,
            retry_policy=worker_policy,
            timeout=worker_timeout,
        )

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._select_next,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""

        return asyncio.run(self.arun(state))

    async def arun(self, state: ResearchState) -> ResearchState:
        """Execute the async graph so node timeouts can be enforced safely."""

        app = self.build()
        result = await app.ainvoke(state)
        return ResearchState.model_validate(result)

    def _run_supervisor(self, state: ResearchState) -> dict[str, Any]:
        with trace_span(
            "workflow.supervisor",
            {
                "iteration": state.iteration,
                "route_history_size": len(state.route_history),
            },
        ) as span:
            state = self.supervisor.run(state)
            span["attributes"]["next_route"] = (
                state.route_history[-1] if state.route_history else "done"
            )
            state.add_trace_event(
                "trace.workflow.supervisor",
                {
                    "span_id": span["span_id"],
                    "route": span["attributes"]["next_route"],
                },
            )
        return state.model_dump()

    async def _run_researcher(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_worker(state, self.researcher)

    async def _run_analyst(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_worker(state, self.analyst)

    async def _run_writer(self, state: ResearchState) -> dict[str, Any]:
        return await self._run_worker(state, self.writer)

    async def _run_worker(self, state: ResearchState, worker: BaseAgent) -> dict[str, Any]:
        with trace_span(
            f"workflow.worker.{worker.name}",
            {
                "iteration": state.iteration,
                "sources": len(state.sources),
                "has_analysis": bool(state.analysis_notes),
            },
        ) as span:
            try:
                state = await asyncio.to_thread(worker.run, state)
                span["attributes"]["status"] = "ok"
                if state.agent_results and state.agent_results[-1].agent.value == worker.name:
                    metadata = state.agent_results[-1].metadata
                    for key in (
                        "provider",
                        "model",
                        "input_tokens",
                        "output_tokens",
                        "cost_usd",
                        "fallback_used",
                    ):
                        if key in metadata:
                            span["attributes"][key] = metadata[key]
            except StudentTodoError as exc:
                # Keep orchestration runnable while learner TODOs are incomplete.
                state.errors.append(str(exc))
                state.add_trace_event("worker.todo", {"agent": worker.name, "error": str(exc)})
                span["attributes"]["status"] = "todo"
            state.add_trace_event(
                f"trace.workflow.worker.{worker.name}",
                {
                    "span_id": span["span_id"],
                    "status": span["attributes"]["status"],
                },
            )
        return state.model_dump()

    @staticmethod
    def _select_next(state: ResearchState) -> str:
        return state.route_history[-1] if state.route_history else "done"
