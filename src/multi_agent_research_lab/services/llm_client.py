"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from openai import OpenAI

from multi_agent_research_lab.core.config import Settings, get_settings


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Small provider-agnostic client with a local no-key fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = (
            OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.timeout_seconds)
            if self.settings.openai_api_key
            else None
        )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return one completion, using OpenAI when configured or local fallback otherwise."""

        if self._client is None:
            return self._local_completion(user_prompt)

        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )

    @staticmethod
    def _local_completion(user_prompt: str) -> LLMResponse:
        """Keep the baseline runnable for students who do not have an API key yet."""

        query = user_prompt.strip()
        content = (
            "Local baseline (no OPENAI_API_KEY configured).\n\n"
            f"Question: {query}\n\n"
            "This deterministic response verifies the single-agent pipeline. "
            "Add OPENAI_API_KEY to .env to replace it with an OpenAI completion."
        )
        input_tokens = max(1, len(query) // 4)
        output_tokens = max(1, len(content) // 4)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
