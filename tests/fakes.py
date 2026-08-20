from types import SimpleNamespace

from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.services.llm_client import LLMClient, LLMResponse


class StubLLMClient(LLMClient):
    """Deterministic completion client that never reaches an external provider."""

    def __init__(self) -> None:
        pass

    @property
    def is_configured(self) -> bool:
        return True

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if "Analyst" in system_prompt:
            content = (
                "Evidence comparison: public references provide architectural support, "
                "while synthetic sources require explicit qualification [stub-source]."
            )
        elif "Writer" in system_prompt:
            content = (
                "The evidence directly addresses the research question and shows that role "
                "specialization can improve traceability when coordination overhead is justified."
            )
        else:
            content = f"Stub baseline answer for: {user_prompt}"
        return LLMResponse(
            content=content,
            input_tokens=20,
            output_tokens=30,
            cost_usd=0.00001,
            provider="stub",
            model="stub-model",
        )


class FailingLLMClient(StubLLMClient):
    """Simulate a provider that remains unavailable after client retries."""

    def __init__(self) -> None:
        self.settings = SimpleNamespace(llm_provider="stub")

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        raise AgentExecutionError("simulated provider outage")
