from __future__ import annotations

import anthropic
import instructor
import openai

from schemakernel.exceptions import PlannerError, PlannerRetryExhausted
from schemakernel.models import PlannerResponse
from schemakernel.policy import PolicyConfig


class PlannerClient:
    def __init__(self, policy: PolicyConfig) -> None:
        self._policy = policy
        self._client = self._build_client()

    def _build_client(self):
        if self._policy.provider == "anthropic":
            raw = anthropic.Anthropic()
            return instructor.from_anthropic(raw)
        elif self._policy.provider == "openai":
            raw = openai.OpenAI(base_url=self._policy.base_url)
            return instructor.from_openai(raw)
        elif self._policy.provider == "ollama":
            # Ollama typically uses the OpenAI compatible endpoint at /v1
            base_url = self._policy.base_url or "http://localhost:11434/v1"
            raw = openai.OpenAI(base_url=base_url, api_key="ollama")
            return instructor.from_openai(raw, mode=instructor.Mode.JSON)
        else:
            raise ValueError(f"Unsupported provider: '{self._policy.provider}'")

    def call(
        self,
        messages: list[dict],
        system_prompt: str,
        *,
        max_retries: int | None = None,
    ) -> PlannerResponse:
        import instructor

        retries = max_retries if max_retries is not None else self._policy.max_retries

        kwargs: dict = {
            "model": self._policy.model,
            "messages": messages,
            "response_model": PlannerResponse,
            "max_retries": retries,
            "temperature": self._policy.temperature,
            "max_tokens": 4096,
        }

        # Anthropic requires system at the top level; OpenAI uses messages
        if self._policy.provider == "anthropic":
            kwargs["system"] = system_prompt
        else:
            kwargs["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            response, _ = self._client.chat.completions.create_with_completion(**kwargs)
            return response
        except Exception as exc:
            # Detect instructor retry exhaustion by class name to avoid version coupling
            if type(exc).__name__ == "InstructorRetryException":
                raise PlannerRetryExhausted(
                    f"Planner failed after {retries} retries: {exc}"
                ) from exc
            raise PlannerError(f"Planner call failed: {exc}") from exc
