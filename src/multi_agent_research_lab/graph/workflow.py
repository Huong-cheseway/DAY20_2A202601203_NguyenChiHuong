"""LangGraph workflow skeleton."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()

    def build(self) -> object:
        """Create a LangGraph graph."""

        graph = StateGraph(dict)
        graph.add_node("supervisor", self._run_supervisor)
        graph.add_node("researcher", self._run_researcher)
        graph.add_node("analyst", self._run_analyst)
        graph.add_node("writer", self._run_writer)

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

        app = self.build()
        result = app.invoke(state.model_dump())
        return ResearchState.model_validate(result)

    def _run_supervisor(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
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

    def _run_researcher(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_worker(payload, self.researcher)

    def _run_analyst(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_worker(payload, self.analyst)

    def _run_writer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_worker(payload, self.writer)

    def _run_worker(self, payload: dict[str, Any], worker: Any) -> dict[str, Any]:
        state = ResearchState.model_validate(payload)
        with trace_span(
            f"workflow.worker.{worker.name}",
            {
                "iteration": state.iteration,
                "sources": len(state.sources),
                "has_analysis": bool(state.analysis_notes),
            },
        ) as span:
            try:
                state = worker.run(state)
                span["attributes"]["status"] = "ok"
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
    def _select_next(payload: dict[str, Any]) -> str:
        state = ResearchState.model_validate(payload)
        return state.route_history[-1] if state.route_history else "done"
