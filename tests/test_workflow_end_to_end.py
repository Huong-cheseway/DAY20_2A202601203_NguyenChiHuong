from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.search_client import SearchClient
from tests.fakes import FailingLLMClient, StubLLMClient


def test_search_client_offline_returns_documents() -> None:
    docs = SearchClient().search("multi-agent architecture benchmark", max_results=3)
    assert len(docs) == 3
    assert all(doc.title for doc in docs)
    assert all(doc.snippet for doc in docs)


def test_search_client_maps_graphrag_to_retrieval_augmented_topic() -> None:
    docs = SearchClient().search("Research GraphRAG state-of-the-art", max_results=3)
    topic_names = {str(doc.metadata.get("topic_name", "")) for doc in docs}
    assert any("Retrieval-Augmented" in topic for topic in topic_names)


def test_multi_agent_workflow_generates_cited_answer() -> None:
    state = ResearchState(
        request=ResearchQuery(
            query="Single-agent vs multi-agent architectures for complex research tasks"
        )
    )
    result = MultiAgentWorkflow(llm_client=StubLLMClient()).run(state)

    assert result.route_history[:4] == ["researcher", "analyst", "writer", "done"]
    assert result.sources
    assert result.research_notes
    assert result.analysis_notes
    assert result.final_answer
    assert "Citations:" in result.final_answer
    assert result.sources[0].title in result.final_answer
    assert {r.agent.value for r in result.agent_results} >= {"researcher", "analyst", "writer"}

    reviewed = CriticAgent().run(result)
    critic_result = next(item for item in reviewed.agent_results if item.agent.value == "critic")
    assert critic_result.metadata["citation_coverage"] == 1.0


def test_multi_agent_workflow_falls_back_after_provider_failure() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent system guardrails"))
    result = MultiAgentWorkflow(llm_client=FailingLLMClient()).run(state)

    assert result.final_answer
    assert not result.errors
    worker_results = [
        item for item in result.agent_results if item.agent.value in {"analyst", "writer"}
    ]
    assert worker_results
    assert all(item.metadata["fallback_used"] is True for item in worker_results)
    assert {event["name"] for event in result.trace} >= {"analyst.fallback", "writer.fallback"}
