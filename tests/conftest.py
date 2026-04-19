from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from schemakernel.models import (
    ActionType,
    CompletionStatus,
    FieldDefinition,
    FieldType,
    PlannerAction,
    PlannerResponse,
    ValidatorRule,
    ValidatorType,
)
from schemakernel.policy import PolicyConfig
from schemakernel.store import InMemoryStore
from schemakernel.validation import ValidationEngine
from schemakernel.workflow import WorkflowStateMachine


@pytest.fixture
def minimal_field() -> FieldDefinition:
    return FieldDefinition(key="name", type=FieldType.TEXT, label="Your name")


@pytest.fixture
def select_field() -> FieldDefinition:
    return FieldDefinition(
        key="country",
        type=FieldType.SELECT,
        label="Country",
        options=["US", "UK", "CA"],
    )


@pytest.fixture
def validated_field() -> FieldDefinition:
    return FieldDefinition(
        key="age",
        type=FieldType.INTEGER,
        label="Age",
        required=True,
        validators=[
            ValidatorRule(type=ValidatorType.MIN, value=0),
            ValidatorRule(type=ValidatorType.MAX, value=120),
        ],
    )


@pytest.fixture
def minimal_policy(minimal_field: FieldDefinition) -> PolicyConfig:
    return PolicyConfig(baseline_questions=[minimal_field], max_turns=5)


@pytest.fixture
def in_memory_store() -> InMemoryStore:
    return InMemoryStore()


def make_add_response(field: FieldDefinition) -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.ADD, field_key=field.key)],
        fields=[field],
        rationale=["Adding field"],
        completion_status=CompletionStatus.IN_PROGRESS,
    )


def make_complete_response() -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.COMPLETE)],
        fields=[],
        rationale=["All done"],
        completion_status=CompletionStatus.COMPLETE,
    )


@pytest.fixture
def mock_planner(validated_field: FieldDefinition):
    planner = MagicMock()
    planner.call.return_value = make_add_response(validated_field)
    return planner


@pytest.fixture
def workflow(minimal_policy: PolicyConfig, in_memory_store: InMemoryStore, mock_planner):
    validator = ValidationEngine(minimal_policy)
    return WorkflowStateMachine(minimal_policy, in_memory_store, mock_planner, validator)
