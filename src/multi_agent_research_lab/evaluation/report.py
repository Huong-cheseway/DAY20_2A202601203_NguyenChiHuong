"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown with trade-off analysis."""

    if not metrics:
        return "# Benchmark Report\n\nNo benchmark rows available.\n"

    lines = [
        "# Benchmark Report",
        "",
        "This report compares the same query set on single-agent baseline",
        "and multi-agent workflow.",
        "Quality is an automated structural proxy (0-10); peer review should validate it.",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation = "" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} "
            f"| {citation} | {failure} | {item.notes} |"
        )

    fastest = min(metrics, key=lambda row: row.latency_seconds)
    cheapest = min(metrics, key=lambda row: row.estimated_cost_usd or 0.0)
    best_quality = max(metrics, key=lambda row: row.quality_score or 0.0)

    lines.extend(
        [
            "",
            "## Key Findings",
            "",
            f"- Fastest run: **{fastest.run_name}** ({fastest.latency_seconds:.2f}s).",
            (
                f"- Lowest estimated cost: **{cheapest.run_name}** "
                f"({(cheapest.estimated_cost_usd or 0.0):.4f} USD)."
            ),
            (
                f"- Highest quality score: **{best_quality.run_name}** "
                f"({(best_quality.quality_score or 0.0):.2f}/10)."
            ),
            "",
            "## Trade-off Notes",
            "",
            "- Multi-agent can be slower or more expensive because it performs",
            "  more handoffs and checks.",
            "- This is expected behavior, not a bug, when quality/citation robustness improves.",
            "- Prefer baseline for simple requests; prefer multi-agent",
            "  when evidence synthesis matters.",
            "",
            "## Failure Mode and Mitigation",
            "",
            "- Provider rate limits (HTTP 429) may increase latency during a benchmark suite.",
            "- The LLM client uses bounded retries and provider timeouts; production runs should",
            "  also pace requests and preserve the provider's Retry-After delay.",
            "- If the LLM remains unavailable, Analyst and Writer use a deterministic fallback",
            "  and mark `fallback_used` in agent metadata and trace events.",
            "",
            "## Trace Evidence",
            "",
            "- Local span log: `reports/trace_spans.jsonl`",
            "- LangSmith project: `multi-agent-research-lab` (when configured).",
        ]
    )
    return "\n".join(lines) + "\n"
