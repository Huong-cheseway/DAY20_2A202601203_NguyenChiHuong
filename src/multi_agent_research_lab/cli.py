"""Command-line entrypoint for the lab starter."""

import sys
from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark_suite
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import flush_traces
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline and report latency and token usage."""

    _init()
    request = _parse_query(query)
    started = perf_counter()
    response = LLMClient().complete(
        system_prompt=(
            "You are a concise research assistant. Answer the user's question accurately "
            "and state uncertainty when evidence is missing."
        ),
        user_prompt=request.query,
    )
    latency = perf_counter() - started
    console.print(Panel.fit(response.content, title="Single-Agent Baseline"))
    console.print(
        f"Latency: {latency:.3f}s | Input tokens: {response.input_tokens or 'N/A'} | "
        f"Output tokens: {response.output_tokens or 'N/A'} | Cost: "
        f"{response.cost_usd if response.cost_usd is not None else 'N/A'}"
    )
    flush_traces()


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=_parse_query(query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    finally:
        flush_traces()
    console.print(result.model_dump_json(indent=2), markup=False)


@app.command()
def benchmark() -> None:
    """Run the configured benchmark suite and write the markdown report."""

    _init()
    config = yaml.safe_load(Path("configs/lab_default.yaml").read_text(encoding="utf-8"))
    raw_queries = config.get("benchmark", {}).get("queries", [])
    queries = [str(query) for query in raw_queries if str(query).strip()]
    if not queries:
        console.print(Panel.fit("No benchmark queries configured.", style="red"))
        raise typer.Exit(code=1)

    try:
        metrics = run_benchmark_suite(queries)
        report = render_markdown_report(metrics)
        path = LocalArtifactStore().write_text("benchmark_report.md", report)
    finally:
        flush_traces()
    console.print(f"Benchmark completed for {len(queries)} queries: {path}")


if __name__ == "__main__":
    app()
