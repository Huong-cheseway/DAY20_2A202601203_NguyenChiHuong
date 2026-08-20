"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from openai import APIError, OpenAI

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError

_GROQ_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
}


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    provider: str = "local"
    model: str | None = None


class LLMClient:
    """OpenAI-compatible client supporting Groq, OpenAI, and a no-key fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.llm_api_key:
            self._client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.timeout_seconds,
                max_retries=self.settings.llm_max_retries,
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return one completion, applying provider timeout and retry settings."""

        if self._client is None:
            return self._local_completion(user_prompt)

        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except APIError as exc:
            raise AgentExecutionError(
                f"{self.settings.llm_provider} completion failed after retries: {exc}"
            ) from exc
        choice = response.choices[0]
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._estimate_cost(input_tokens, output_tokens),
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
        )

    def _estimate_cost(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if self.settings.llm_provider != "groq":
            return None
        prices = _GROQ_PRICES_PER_MILLION.get(self.settings.llm_model)
        if prices is None or input_tokens is None or output_tokens is None:
            return None
        input_rate, output_rate = prices
        return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

    @staticmethod
    def _local_completion(user_prompt: str) -> LLMResponse:
        """Keep the baseline runnable for students who do not have an API key yet."""

        query = user_prompt.strip()
        content = (
            "Local baseline (no LLM API key configured).\n\n"
            f"Question: {query}\n\n"
            "This deterministic response verifies the single-agent pipeline. "
            "Add GROQ_API_KEY or OPENAI_API_KEY to .env to use a real completion."
        )
        input_tokens = max(1, len(query) // 4)
        output_tokens = max(1, len(content) // 4)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
        )
