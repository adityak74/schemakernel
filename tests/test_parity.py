from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemakernel.models import (
    ConditionalLogic,
    FieldDefinition,
    PlannerResponse,
    SchemaState,
)
from schemakernel.validation import ValidationEngine
from schemakernel.workflow import WorkflowStateMachine
from schemakernel.policy import PolicyConfig
from unittest.mock import MagicMock
from schemakernel.store import InMemoryStore


VECTORS_DIR = Path(__file__).parent.parent / "vectors"


def load_vector(name: str):
    with open(VECTORS_DIR / f"{name}_vectors.json") as f:
        return json.load(f)


@pytest.mark.parametrize("case", load_vector("validation"))
def test_validation_parity(case):
    engine = ValidationEngine(PolicyConfig())
    field = FieldDefinition.model_validate(case["field"])
    result = engine.validate_answer(field, case["answer"])
    assert result.valid == case["expected_valid"], f"Failed case: {case['name']}"


@pytest.mark.parametrize("case", load_vector("condition"))
def test_condition_parity(case):
    # We use WorkflowStateMachine's internal _evaluate_condition to test parity
    wf = WorkflowStateMachine(PolicyConfig(), InMemoryStore(), MagicMock(), ValidationEngine(PolicyConfig()))
    logic = ConditionalLogic.model_validate(case["logic"])
    result = wf._evaluate_condition(logic, case["answers"])
    assert result == case["expected"], f"Failed case: {case['name']}"


@pytest.mark.parametrize("case", load_vector("workflow"))
def test_workflow_parity(case):
    wf = WorkflowStateMachine(PolicyConfig(), InMemoryStore(), MagicMock(), ValidationEngine(PolicyConfig()))
    initial_state = SchemaState.model_validate(case["initial_state"])
    response = PlannerResponse.model_validate(case["response"])
    
    # Manually apply transition logic that run_planner_turn uses
    new_state = initial_state.model_copy(deep=True)
    wf._apply_actions(new_state, response)
    
    if "expected_fields" in case and case["expected_fields"] is not None:
        assert sorted(list(new_state.fields.keys())) == sorted(case["expected_fields"])
    
    if "expected_stage" in case and case["expected_stage"] is not None:
        assert new_state.stage.value == case["expected_stage"]
        
    if "expected_order" in case and case["expected_order"] is not None:
        assert new_state.field_order == case["expected_order"]
