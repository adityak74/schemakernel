from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from schemakernel.exceptions import PlannerError, PlannerRetryExhausted
from schemakernel.models import (
    ActionType,
    CompletionStatus,
    FieldDefinition,
    FieldType,
    PlannerAction,
    PlannerResponse,
)
from schemakernel.planner import PlannerClient
from schemakernel.policy import PolicyConfig


def anthropic_policy(**kw) -> PolicyConfig:
    return PolicyConfig(provider="anthropic", **kw)


def openai_policy(**kw) -> PolicyConfig:
    return PolicyConfig(provider="openai", **kw)


def make_response() -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.COMPLETE)],
        fields=[],
        rationale=["done"],
        completion_status=CompletionStatus.COMPLETE,
    )


class TestPlannerClient:
    def test_builds_anthropic_client(self):
        with (
            patch("schemakernel.planner.instructor") as mock_inst,
            patch("schemakernel.planner.anthropic") as mock_ant,
        ):
            mock_inst.from_anthropic.return_value = MagicMock()
            PlannerClient(anthropic_policy())
            mock_inst.from_anthropic.assert_called_once()

    def test_builds_openai_client(self):
        with (
            patch("schemakernel.planner.instructor") as mock_inst,
            patch("schemakernel.planner.openai") as mock_oi,
        ):
            mock_inst.from_openai.return_value = MagicMock()
            PlannerClient(openai_policy())
            mock_inst.from_openai.assert_called_once()

    def test_unsupported_provider_raises(self):
        policy = PolicyConfig.model_construct(
            provider="unknown",
            model="claude-sonnet-4-6",
            temperature=0.2,
            max_retries=3,
        )
        with (
            patch("schemakernel.planner.instructor"),
            patch("schemakernel.planner.anthropic"),
        ):
            with pytest.raises(ValueError, match="Unsupported provider"):
                PlannerClient(policy)

    def test_returns_typed_response(self):
        expected = make_response()
        with (
            patch("schemakernel.planner.instructor") as mock_inst,
            patch("schemakernel.planner.anthropic"),
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create_with_completion.return_value = (
                expected,
                MagicMock(),
            )
            mock_inst.from_anthropic.return_value = mock_client

            pc = PlannerClient(anthropic_policy())
            result = pc.call([{"role": "user", "content": "go"}], "system")
            assert result is expected

    def test_retry_exhausted_raises_custom_exception(self):
        from instructor.core import InstructorRetryException

        with (
            patch("schemakernel.planner.instructor") as mock_inst,
            patch("schemakernel.planner.anthropic"),
        ):
            mock_client = MagicMock()
            mock_client.chat.completions.create_with_completion.side_effect = (
                InstructorRetryException("fail", n_attempts=3, total_usage=0)
            )
            mock_inst.from_anthropic.return_value = mock_client

            pc = PlannerClient(anthropic_policy())
            with pytest.raises(PlannerRetryExhausted):
                pc.call([], "system")
