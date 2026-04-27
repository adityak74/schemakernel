from __future__ import annotations

from unittest.mock import MagicMock

from schemakernel.models import (
    ActionType,
    CompletionStatus,
    FieldDefinition,
    FieldType,
    PlannerAction,
    PlannerResponse,
    WorkflowStage,
)
from schemakernel.policy import PolicyConfig
from schemakernel.store import InMemoryStore
from schemakernel.validation import ValidationEngine
from schemakernel.workflow import WorkflowStateMachine


def test_multi_turn_integration():
    # Setup
    baseline = [
        FieldDefinition(key="first_name", type=FieldType.TEXT, label="First Name"),
        FieldDefinition(key="last_name", type=FieldType.TEXT, label="Last Name"),
    ]
    policy = PolicyConfig(baseline_questions=baseline)
    store = InMemoryStore()
    mock_planner = MagicMock()
    validator = ValidationEngine(policy)
    wf = WorkflowStateMachine(policy, store, mock_planner, validator)

    # 1. Start Session
    state = wf.start_session(session_id="test-session")
    assert "first_name" in state.fields
    assert "last_name" in state.fields
    assert state.stage == WorkflowStage.COLLECTING

    # 2. Submit initial answers
    wf.submit_answer("test-session", "first_name", "Alice")
    wf.submit_answer("test-session", "last_name", "Smith")

    # 3. First Planner Turn: Add email field
    email_field = FieldDefinition(key="email", type=FieldType.EMAIL, label="Email Address")
    mock_planner.call.return_value = PlannerResponse(
        actions=[PlannerAction(action=ActionType.ADD, field_key="email")],
        fields=[email_field],
        rationale=["We need an email to contact you."],
        completion_status=CompletionStatus.IN_PROGRESS,
    )

    state = wf.run_planner_turn("test-session")
    assert "email" in state.fields
    assert state.turn_count == 1
    assert state.stage == WorkflowStage.COLLECTING

    # 4. Submit answer for new field
    res = wf.submit_answer("test-session", "email", "alice@example.com")
    assert res.valid

    # 5. Second Planner Turn: Complete
    mock_planner.call.return_value = PlannerResponse(
        actions=[PlannerAction(action=ActionType.COMPLETE)],
        fields=[],
        rationale=["All information collected."],
        completion_status=CompletionStatus.COMPLETE,
    )

    state = wf.run_planner_turn("test-session")
    assert state.stage == WorkflowStage.COMPLETE
    assert state.turn_count == 2

    # 6. Final verification
    final_state = wf.get_state("test-session")
    assert final_state.answers == {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
    }

    traces = store.list_traces("test-session")
    assert len(traces) == 2
    assert traces[0].raw_response["actions"][0]["action"] == ActionType.ADD
    assert traces[1].raw_response["actions"][0]["action"] == ActionType.COMPLETE
