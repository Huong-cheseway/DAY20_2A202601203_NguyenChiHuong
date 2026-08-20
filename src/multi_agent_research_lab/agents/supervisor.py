"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""

        settings = get_settings()

        if state.iteration >= settings.max_iterations or state.final_answer or state.errors:
            route = "done"
        elif not state.sources:
            route = "researcher"
        elif not state.analysis_notes:
            route = "analyst"
        else:
            route = "writer"

        state.record_route(route)
        state.add_trace_event(
            "supervisor.route",
            {
                "route": route,
                "iteration": state.iteration,
                "max_iterations": settings.max_iterations,
            },
        )
        return state
