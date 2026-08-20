"""Search client abstraction for ResearcherAgent."""

import json
import re
from pathlib import Path
from typing import Any

from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Offline-first search client for local benchmark corpus retrieval."""

    _STOPWORDS = {
        "and",
        "art",
        "compare",
        "for",
        "research",
        "state",
        "summary",
        "the",
        "write",
    }

    _CORPUS_TOPICS_DIR = (
        Path(__file__).resolve().parents[3]
        / "ai_agent_offline_research_corpus_30_topics_v2"
        / "topics"
    )

    def __init__(self, topics_dir: Path | None = None) -> None:
        self._topics_dir = topics_dir or self._CORPUS_TOPICS_DIR
        self._topics_cache = self._load_topics()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search local corpus for relevant source documents.

        If corpus files are unavailable, return deterministic fallback documents so
        the lab pipeline remains runnable without external APIs.
        """

        if not self._topics_cache:
            return self._fallback_documents(query, max_results)

        query_terms = self._tokenize(query)
        candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for topic in self._topics_cache:
            topic_score = self._topic_score(topic, query_terms)
            sources = topic.get("knowledge_base", {}).get("source_documents", [])
            for source in sources:
                source_score = self._source_score(source, query_terms)
                candidates.append((topic_score + (source_score * 2), topic, source))
        candidates.sort(key=lambda item: item[0], reverse=True)

        selected: list[SourceDocument] = []
        seen_documents: set[str] = set()
        for _, topic, source in candidates:
            document_id = str(source.get("document_id", "unknown"))
            dedupe_key = f"{document_id}:{source.get('title', '')}"
            if dedupe_key in seen_documents:
                continue
            seen_documents.add(dedupe_key)
            title = str(source.get("title", "Untitled source"))
            full_text = str(source.get("full_text", ""))
            snippet = self._to_snippet(full_text)
            selected.append(
                SourceDocument(
                    title=title,
                    url=source.get("provenance_url"),
                    snippet=snippet,
                    metadata={
                        "document_id": document_id,
                        "document_class": source.get("document_class"),
                        "is_synthetic": bool(source.get("is_synthetic", False)),
                        "topic_id": topic.get("benchmark_metadata", {}).get("topic_id"),
                        "topic_name": topic.get("topic", {}).get("name"),
                    },
                )
            )
            if len(selected) >= max(1, max_results):
                break
        return selected

    def _load_topics(self) -> list[dict[str, Any]]:
        if not self._topics_dir.exists():
            return []

        topics: list[dict[str, Any]] = []
        for path in sorted(self._topics_dir.glob("*.json")):
            try:
                topics.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return topics

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        normalized = re.sub(
            r"\bgraphrag\b",
            "graph rag retrieval augmented generation",
            text.lower(),
        )
        return {
            token
            for token in re.findall(r"[a-z0-9]+", normalized)
            if len(token) > 2 and token not in SearchClient._STOPWORDS
        }

    def _topic_score(self, topic_payload: dict[str, Any], query_terms: set[str]) -> int:
        topic = topic_payload.get("topic", {})
        haystack = " ".join(
            [
                str(topic.get("name", "")),
                str(topic.get("research_question", "")),
                " ".join(str(tag) for tag in topic.get("tags", [])),
            ]
        )
        topic_terms = self._tokenize(haystack)
        overlap = len(topic_terms & query_terms)
        return overlap + (1 if topic.get("name") else 0)

    def _source_score(self, source_payload: dict[str, Any], query_terms: set[str]) -> int:
        haystack = " ".join(
            [
                str(source_payload.get("title", "")),
                str(source_payload.get("document_class", "")),
                str(source_payload.get("full_text", ""))[:1500],
            ]
        )
        return len(self._tokenize(haystack) & query_terms)

    @staticmethod
    def _to_snippet(text: str, limit: int = 320) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3]}..."

    @staticmethod
    def _fallback_documents(query: str, max_results: int) -> list[SourceDocument]:
        docs = [
            SourceDocument(
                title="Offline corpus not found: baseline architecture note",
                url=None,
                snippet=(
                    "Use a simple baseline first, then add role specialization and evaluate "
                    "quality, latency, and cost trade-offs."
                ),
                metadata={"document_id": "fallback-1", "query": query},
            ),
            SourceDocument(
                title="Offline corpus not found: coordination risk note",
                url=None,
                snippet=(
                    "Multi-agent systems can improve coverage but may regress due to handoff "
                    "errors and duplicated work without guardrails."
                ),
                metadata={"document_id": "fallback-2", "query": query},
            ),
        ]
        return docs[: max(1, max_results)]
