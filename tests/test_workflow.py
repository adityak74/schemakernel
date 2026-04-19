from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from schemakernel.exceptions import PlannerOutputRejected, TurnLimitExceeded
from schemakernel.models import (
    ActionType,
    CompletionStatus,
    Condition,
    ConditionalLogic,
    ConditionOperator,
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


def make_wf(policy: PolicyConfig | None = None, planner=None):
    p = policy or PolicyConfig()
    store = InMemoryStore()
    mock_p = planner or MagicMock()
    validator = ValidationEngine(p)
    return WorkflowStateMachine(p, store, mock_p, validator), store, mock_p


def make_add_response(field: FieldDefinition) -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.ADD, field_key=field.key)],
        fields=[field],
        rationale=["adding"],
        completion_status=CompletionStatus.IN_PROGRESS,
    )


def make_complete_response() -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.COMPLETE)],
        fields=[],
        rationale=["done"],
        completion_status=CompletionStatus.COMPLETE,
    )


def make_field(key="extra", ftype=FieldType.TEXT) -> FieldDefinition:
    opts = ["a", "b"] if ftype in (FieldType.SELECT, FieldType.MULTISELECT) else None
    return FieldDefinition(key=key, type=ftype, label=key.title(), options=opts)


class TestStartSession:
    def test_applies_baseline_questions(self):
        fd = make_field("name")
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        assert "name" in state.fields
        assert state.stage == WorkflowStage.COLLECTING

    def test_generates_uuid_if_no_id(self):
        wf, _, _ = make_wf()
        state = wf.start_session()
        assert len(state.session_id) == 36

    def test_uses_provided_session_id(self):
        wf, _, _ = make_wf()
        state = wf.start_session(session_id="custom-id")
        assert state.session_id == "custom-id"


class TestSubmitAnswer:
    def test_valid_answer_recorded(self):
        fd = make_field("name")
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        result = wf.submit_answer(state.session_id, "name", "Alice")
        assert result.valid
        reloaded = wf.get_state(state.session_id)
        assert reloaded.answers["name"] == "Alice"

    def test_invalid_answer_not_recorded(self):
        from schemakernel.models import ValidatorRule, ValidatorType
        fd = FieldDefinition(
            key="age", type=FieldType.INTEGER, label="Age",
            validators=[ValidatorRule(type=ValidatorType.MIN, value=0)],
        )
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        result = wf.submit_answer(state.session_id, "age", -5)
        assert not result.valid
        reloaded = wf.get_state(state.session_id)
        assert "age" not in reloaded.answers

    def test_nonexistent_field_returns_invalid(self):
        wf, _, _ = make_wf()
        state = wf.start_session()
        result = wf.submit_answer(state.session_id, "ghost", "val")
        assert not result.valid


class TestRunPlannerTurn:
    def test_add_action_adds_field(self):
        new_fd = make_field("email")
        wf, _, mock_p = make_wf()
        mock_p.call.return_value = make_add_response(new_fd)
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert "email" in state.fields

    def test_update_action_updates_field(self):
        fd = make_field("name")
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, mock_p = make_wf(policy)
        updated_fd = FieldDefinition(key="name", type=FieldType.TEXT, label="Full Name")
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.UPDATE, field_key="name")],
            fields=[updated_fd],
            rationale=["updating label"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        mock_p.call.return_value = response
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert state.fields["name"].label == "Full Name"

    def test_remove_action_removes_field(self):
        fd = make_field("name")
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, mock_p = make_wf(policy)
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.REMOVE, field_key="name")],
            fields=[],
            rationale=["removing"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        mock_p.call.return_value = response
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert "name" not in state.fields

    def test_complete_action_transitions_stage(self):
        wf, _, mock_p = make_wf()
        mock_p.call.return_value = make_complete_response()
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert state.stage == WorkflowStage.COMPLETE

    def test_escalate_action_transitions_stage(self):
        wf, _, mock_p = make_wf()
        mock_p.call.return_value = PlannerResponse(
            actions=[PlannerAction(action=ActionType.ESCALATE)],
            fields=[],
            rationale=["escalating"],
            completion_status=CompletionStatus.ESCALATE,
        )
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert state.stage == WorkflowStage.ESCALATED

    def test_turn_count_increments(self):
        new_fd = make_field("extra")
        wf, _, mock_p = make_wf()
        mock_p.call.return_value = make_add_response(new_fd)
        state = wf.start_session()
        state = wf.run_planner_turn(state.session_id)
        assert state.turn_count == 1

    def test_turn_limit_exceeded_raises(self):
        policy = PolicyConfig(max_turns=1)
        wf, store, mock_p = make_wf(policy)
        new_fd = make_field("e")
        mock_p.call.return_value = make_add_response(new_fd)
        state = wf.start_session()
        wf.run_planner_turn(state.session_id)
        with pytest.raises(TurnLimitExceeded):
            wf.run_planner_turn(state.session_id)

    def test_invalid_response_raises_planner_output_rejected(self):
        # Response tries to UPDATE a non-existent field
        bad_fd = make_field("ghost")
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.UPDATE, field_key="ghost")],
            fields=[bad_fd],
            rationale=["bad"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        wf, _, mock_p = make_wf()
        mock_p.call.return_value = response
        state = wf.start_session()
        with pytest.raises(PlannerOutputRejected):
            wf.run_planner_turn(state.session_id)

    def test_trace_saved_on_success(self):
        new_fd = make_field("extra")
        wf, store, mock_p = make_wf()
        mock_p.call.return_value = make_add_response(new_fd)
        state = wf.start_session()
        wf.run_planner_turn(state.session_id)
        traces = store.list_traces(state.session_id)
        assert len(traces) == 1
        assert traces[0].validated is True

    def test_trace_saved_on_rejection(self):
        bad_fd = make_field("ghost")
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.UPDATE, field_key="ghost")],
            fields=[bad_fd],
            rationale=["bad"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        wf, store, mock_p = make_wf()
        mock_p.call.return_value = response
        state = wf.start_session()
        with pytest.raises(PlannerOutputRejected):
            wf.run_planner_turn(state.session_id)
        traces = store.list_traces(state.session_id)
        assert len(traces) == 1
        assert traces[0].validated is False


class TestGetNextFields:
    def test_respects_visible_if(self):
        trigger = make_field("trigger")
        dependent = FieldDefinition(
            key="dep",
            type=FieldType.TEXT,
            label="Dep",
            visible_if=ConditionalLogic(
                conditions=[
                    Condition(
                        field_key="trigger",
                        operator=ConditionOperator.EQ,
                        value="yes",
                    )
                ]
            ),
        )
        policy = PolicyConfig(baseline_questions=[trigger, dependent])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        # Without trigger answered, dep should not appear
        fields = wf.get_next_fields(state.session_id)
        assert all(f.key != "dep" for f in fields)

    def test_visible_if_satisfied_shows_field(self):
        trigger = make_field("trigger")
        dependent = FieldDefinition(
            key="dep",
            type=FieldType.TEXT,
            label="Dep",
            visible_if=ConditionalLogic(
                conditions=[
                    Condition(
                        field_key="trigger",
                        operator=ConditionOperator.EQ,
                        value="yes",
                    )
                ]
            ),
        )
        policy = PolicyConfig(baseline_questions=[trigger, dependent])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        wf.submit_answer(state.session_id, "trigger", "yes")
        fields = wf.get_next_fields(state.session_id)
        assert any(f.key == "dep" for f in fields)

    def test_answered_field_excluded(self):
        fd = make_field("name")
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        wf.submit_answer(state.session_id, "name", "Alice")
        fields = wf.get_next_fields(state.session_id)
        assert all(f.key != "name" for f in fields)

    def test_ask_if_missing_false_excluded(self):
        fd = FieldDefinition(
            key="hidden", type=FieldType.TEXT, label="H", ask_if_missing=False
        )
        policy = PolicyConfig(baseline_questions=[fd])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        fields = wf.get_next_fields(state.session_id)
        assert all(f.key != "hidden" for f in fields)

    def test_sorted_by_priority(self):
        f1 = FieldDefinition(key="low", type=FieldType.TEXT, label="L", priority=200)
        f2 = FieldDefinition(key="high", type=FieldType.TEXT, label="H", priority=10)
        policy = PolicyConfig(baseline_questions=[f1, f2])
        wf, _, _ = make_wf(policy)
        state = wf.start_session()
        fields = wf.get_next_fields(state.session_id)
        assert fields[0].key == "high"
        assert fields[1].key == "low"


class TestConditionEvaluation:
    def _make_wf(self):
        wf, _, _ = make_wf()
        return wf

    def test_eq_true(self):
        wf = self._make_wf()
        c = Condition(field_key="x", operator=ConditionOperator.EQ, value="yes")
        logic = ConditionalLogic(conditions=[c])
        assert wf._evaluate_condition(logic, {"x": "yes"})

    def test_eq_false(self):
        wf = self._make_wf()
        c = Condition(field_key="x", operator=ConditionOperator.EQ, value="yes")
        logic = ConditionalLogic(conditions=[c])
        assert not wf._evaluate_condition(logic, {"x": "no"})

    def test_in_operator(self):
        wf = self._make_wf()
        c = Condition(field_key="x", operator=ConditionOperator.IN, value=["a", "b"])
        logic = ConditionalLogic(conditions=[c])
        assert wf._evaluate_condition(logic, {"x": "a"})
        assert not wf._evaluate_condition(logic, {"x": "c"})

    def test_is_empty_operator(self):
        wf = self._make_wf()
        c = Condition(field_key="x", operator=ConditionOperator.IS_EMPTY)
        logic = ConditionalLogic(conditions=[c])
        assert wf._evaluate_condition(logic, {})
        assert wf._evaluate_condition(logic, {"x": ""})
        assert not wf._evaluate_condition(logic, {"x": "val"})

    def test_gt_operator(self):
        wf = self._make_wf()
        c = Condition(field_key="age", operator=ConditionOperator.GT, value=18)
        logic = ConditionalLogic(conditions=[c])
        assert wf._evaluate_condition(logic, {"age": 25})
        assert not wf._evaluate_condition(logic, {"age": 10})

    def test_or_combinator(self):
        wf = self._make_wf()
        logic = ConditionalLogic(
            combinator="or",
            conditions=[
                Condition(field_key="x", operator=ConditionOperator.EQ, value="a"),
                Condition(field_key="x", operator=ConditionOperator.EQ, value="b"),
            ],
        )
        assert wf._evaluate_condition(logic, {"x": "a"})
        assert wf._evaluate_condition(logic, {"x": "b"})
        assert not wf._evaluate_condition(logic, {"x": "c"})
