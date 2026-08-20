"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

_TRACE_PATH = Path(os.getenv("TRACE_LOG_PATH", "reports/trace_spans.jsonl"))


def _detect_backend() -> str:
    if os.getenv("LANGSMITH_API_KEY"):
        return "langsmith"
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        return "langfuse"
    return "local"


def _write_span(span: dict[str, Any]) -> None:
    _TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(span, ensure_ascii=True) + "\n")


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Minimal span context used by the skeleton.

    TODO(student): Replace or augment with LangSmith/Langfuse provider spans.
    """

    started = perf_counter()
    span: dict[str, Any] = {
        "span_id": str(uuid4()),
        "name": name,
        "backend": _detect_backend(),
        "started_at": datetime.now(UTC).isoformat(),
        "attributes": attributes or {},
        "duration_seconds": None,
    }
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
        span["finished_at"] = datetime.now(UTC).isoformat()
        _write_span(span)
