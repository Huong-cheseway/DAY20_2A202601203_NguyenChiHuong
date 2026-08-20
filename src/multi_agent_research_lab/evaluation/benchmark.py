"""Benchmark skeleton for single-agent vs multi-agent."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient

Runner = Callable[[str], ResearchState]

_ESTIMATED_USD_PER_1K_TOKENS = 0.00015


def _compute_citation_coverage(state: ResearchState) -> float:
    if not state.sources or not state.final_answer:
        return 0.0

    answer = state.final_answer.lower()
    covered = 0
    for doc in state.sources:
        doc_id = str(doc.metadata.get("document_id", "")).lower()
        title = doc.title.lower()
        url = (doc.url or "").lower()
        if (doc_id and f"[{doc_id}]" in answer) or title in answer or (url and url in answer):
            covered += 1
    return covered / len(state.sources)


def _estimate_tokens(state: ResearchState) -> int:
    from_agent_results = 0
    for result in state.agent_results:
        value = result.metadata.get("estimated_tokens")
        if isinstance(value, int):
            from_agent_results += value
    if from_agent_results > 0:
        return from_agent_results

    text_parts = [
        state.research_notes or "",
        state.analysis_notes or "",
        state.final_answer or "",
    ]
    return max(1, sum(len(part) for part in text_parts) // 4)


def _estimate_cost_usd(state: ResearchState) -> float:
    explicit_costs = [
        event["payload"].get("cost_usd")
        for event in state.trace
        if isinstance(event.get("payload"), dict)
        and isinstance(event["payload"].get("cost_usd"), (int, float))
    ]
    if explicit_costs:
        return float(sum(float(v) for v in explicit_costs))

    estimated_tokens = _estimate_tokens(state)
    return (estimated_tokens / 1000) * _ESTIMATED_USD_PER_1K_TOKENS


def _score_quality(state: ResearchState, citation_coverage: float) -> float:
    score = 0.0
    if state.final_answer:
        score += 3.0
    if state.research_notes:
        score += 2.0
    if state.analysis_notes:
        score += 2.0
    if state.sources:
        score += 1.0
    score += citation_coverage * 2.0
    if not state.errors:
        score += 0.5
    return min(10.0, round(score, 2))


def run_single_agent_baseline(query: str, llm_client: LLMClient | None = None) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    with trace_span("benchmark.single_agent"):
        response = (llm_client or LLMClient()).complete(
            system_prompt=(
                "You are a concise research assistant. Answer accurately and "
                "state uncertainty when evidence is missing."
            ),
            user_prompt=query,
        )
    state.final_answer = response.content
    state.add_trace_event(
        "baseline.done",
        {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
            "estimated_tokens": (response.input_tokens or 0) + (response.output_tokens or 0),
        },
    )
    return state


def run_multi_agent_pipeline(query: str, llm_client: LLMClient | None = None) -> ResearchState:
    with trace_span("benchmark.multi_agent"):
        state = ResearchState(request=ResearchQuery(query=query))
        return MultiAgentWorkflow(llm_client=llm_client).run(state)


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency/cost/quality and return metrics for one run."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    citation_coverage = _compute_citation_coverage(state)
    quality_score = _score_quality(state, citation_coverage)
    failure_rate = 1.0 if state.errors else 0.0
    estimated_cost = _estimate_cost_usd(state)
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=estimated_cost,
        quality_score=quality_score,
        citation_coverage=citation_coverage,
        failure_rate=failure_rate,
        notes=(
            f"sources={len(state.sources)}; route_steps={len(state.route_history)}; "
            f"errors={len(state.errors)}"
        ),
    )
    return state, metrics


def run_benchmark_suite(
    queries: list[str], llm_client: LLMClient | None = None
) -> list[BenchmarkMetrics]:
    """Run baseline and multi-agent for each query, then average by run_name."""

    def baseline_runner(item: str) -> ResearchState:
        return run_single_agent_baseline(item, llm_client)

    def multi_runner(item: str) -> ResearchState:
        return run_multi_agent_pipeline(item, llm_client)

    rows: list[BenchmarkMetrics] = []
    for query in queries:
        rows.append(run_benchmark("single_agent", query, baseline_runner)[1])
        rows.append(run_benchmark("multi_agent", query, multi_runner)[1])

    aggregated: dict[str, list[BenchmarkMetrics]] = {"single_agent": [], "multi_agent": []}
    for row in rows:
        aggregated[row.run_name].append(row)

    summary: list[BenchmarkMetrics] = []
    for run_name in ("single_agent", "multi_agent"):
        group = aggregated[run_name]
        size = len(group)
        summary.append(
            BenchmarkMetrics(
                run_name=run_name,
                latency_seconds=sum(item.latency_seconds for item in group) / size,
                estimated_cost_usd=sum((item.estimated_cost_usd or 0.0) for item in group) / size,
                quality_score=sum((item.quality_score or 0.0) for item in group) / size,
                citation_coverage=sum((item.citation_coverage or 0.0) for item in group) / size,
                failure_rate=sum((item.failure_rate or 0.0) for item in group) / size,
                notes=f"averaged over {size} queries",
            )
        )
    return summary
