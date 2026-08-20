"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

import json
import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from langsmith import Client, trace

from multi_agent_research_lab.core.config import get_settings

_TRACE_PATH = Path(os.getenv("TRACE_LOG_PATH", "reports/trace_spans.jsonl"))


def _detect_backend() -> str:
    settings = get_settings()
    if settings.langsmith_tracing and settings.langsmith_api_key:
        return "langsmith"
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        return "langfuse"
    return "local"


@lru_cache(maxsize=1)
def _get_langsmith_client() -> Client | None:
    settings = get_settings()
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        return None
    return Client(api_key=settings.langsmith_api_key)


def _write_span(span: dict[str, Any]) -> None:
    if get_settings().app_env == "test":
        return
    _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(span, ensure_ascii=True) + "\n")


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Write a local JSON span and mirror it to LangSmith when configured."""

    started = perf_counter()
    span: dict[str, Any] = {
        "span_id": str(uuid4()),
        "name": name,
        "backend": _detect_backend(),
        "started_at": datetime.now(UTC).isoformat(),
        "attributes": attributes or {},
        "duration_seconds": None,
    }
    with ExitStack() as stack:
        remote_run: Any = None
        client = _get_langsmith_client()
        if client is not None:
            try:
                remote_run = stack.enter_context(
                    trace(
                        name,
                        run_type="chain",
                        inputs=dict(span["attributes"]),
                        project_name=get_settings().langsmith_project,
                        client=client,
                    )
                )
            except Exception as exc:  # tracing must never break the workflow
                span["attributes"]["langsmith_error"] = type(exc).__name__

        try:
            yield span
        finally:
            span["duration_seconds"] = perf_counter() - started
            span["finished_at"] = datetime.now(UTC).isoformat()
            if remote_run is not None:
                remote_run.end(outputs={"attributes": span["attributes"]})
            _write_span(span)


def flush_traces() -> bool:
    """Flush pending LangSmith spans; return whether a remote client was active."""

    client = _get_langsmith_client()
    if client is None:
        return False
    try:
        client.flush(timeout=10)
    except Exception:
        return False
    return True
