"""Routing policy tests for the Step 2 supervisor implementation."""

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_researcher_when_sources_missing() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    updated = SupervisorAgent().run(state)
    assert updated.route_history[-1] == "researcher"


def test_supervisor_stops_on_max_iterations() -> None:
    settings = get_settings()
    state = ResearchState(
        request=ResearchQuery(query="Explain multi-agent systems"),
        iteration=settings.max_iterations,
    )
    updated = SupervisorAgent().run(state)
    assert updated.route_history[-1] == "done"
