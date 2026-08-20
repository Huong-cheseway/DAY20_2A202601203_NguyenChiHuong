from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.search_client import SearchClient


def test_search_client_offline_returns_documents() -> None:
    docs = SearchClient().search("multi-agent architecture benchmark", max_results=3)
    assert len(docs) == 3
    assert all(doc.title for doc in docs)
    assert all(doc.snippet for doc in docs)


def test_multi_agent_workflow_generates_cited_answer() -> None:
    state = ResearchState(
        request=ResearchQuery(
            query="Single-agent vs multi-agent architectures for complex research tasks"
        )
    )
    result = MultiAgentWorkflow().run(state)

    assert result.route_history[:4] == ["researcher", "analyst", "writer", "done"]
    assert result.sources
    assert result.research_notes
    assert result.analysis_notes
    assert result.final_answer
    assert "Citations:" in result.final_answer
    assert result.sources[0].title in result.final_answer
    assert {r.agent.value for r in result.agent_results} >= {"researcher", "analyst", "writer"}