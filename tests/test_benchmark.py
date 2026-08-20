from multi_agent_research_lab.evaluation.benchmark import (
    run_benchmark,
    run_benchmark_suite,
    run_multi_agent_pipeline,
    run_single_agent_baseline,
)
from tests.fakes import StubLLMClient


def test_run_benchmark_populates_metrics() -> None:
    _, metrics = run_benchmark(
        "multi_agent",
        "Single-agent vs multi-agent architectures for complex research tasks",
        lambda query: run_multi_agent_pipeline(query, StubLLMClient()),
    )
    assert metrics.latency_seconds >= 0
    assert metrics.estimated_cost_usd is not None
    assert metrics.quality_score is not None
    assert metrics.citation_coverage is not None
    assert metrics.failure_rate is not None


def test_run_benchmark_suite_returns_aggregated_rows() -> None:
    metrics = run_benchmark_suite(
        [
            "Single-agent vs multi-agent architectures for complex research tasks",
            "Cost latency and parallelism in multi-agent research",
        ],
        llm_client=StubLLMClient(),
    )
    run_names = {item.run_name for item in metrics}
    assert run_names == {"single_agent", "multi_agent"}
    assert len(metrics) == 2


def test_baseline_runner_returns_final_answer() -> None:
    state = run_single_agent_baseline("Explain multi-agent systems", StubLLMClient())
    assert state.final_answer
