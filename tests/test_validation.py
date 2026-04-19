from __future__ import annotations

import pytest

from schemakernel.exceptions import FieldValidationError, PlannerOutputRejected
from schemakernel.models import (
    ActionType,
    CompletionStatus,
    FieldDefinition,
    FieldType,
    PlannerAction,
    PlannerResponse,
    SchemaState,
    ValidatorRule,
    ValidatorType,
)
from schemakernel.policy import PolicyConfig
from schemakernel.validation import ValidationEngine


def make_engine(policy: PolicyConfig | None = None) -> ValidationEngine:
    return ValidationEngine(policy or PolicyConfig())


def make_state(fields: dict | None = None) -> SchemaState:
    state = SchemaState(session_id="test")
    if fields:
        state.fields = fields
        state.field_order = list(fields.keys())
    return state


def text_field(key="f") -> FieldDefinition:
    return FieldDefinition(key=key, type=FieldType.TEXT, label="F")


def int_field(key="n", validators=None) -> FieldDefinition:
    return FieldDefinition(
        key=key, type=FieldType.INTEGER, label="N", validators=validators or []
    )


# ------------------------------------------------------------------
# Answer validation
# ------------------------------------------------------------------


class TestAnswerValidation:
    def test_required_passes_with_value(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.REQUIRED)],
        )
        result = make_engine().validate_answer(fd, "hello")
        assert result.valid

    def test_required_fails_on_empty_string(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.REQUIRED)],
        )
        result = make_engine().validate_answer(fd, "")
        assert not result.valid
        assert result.errors[0].key == "f"

    def test_required_fails_on_none(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.REQUIRED)],
        )
        result = make_engine().validate_answer(fd, None)
        assert not result.valid

    def test_min_passes_in_range(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.MIN, value=0)])
        assert make_engine().validate_answer(fd, 5).valid

    def test_min_fails_below_range(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.MIN, value=0)])
        assert not make_engine().validate_answer(fd, -1).valid

    def test_max_passes_in_range(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.MAX, value=100)])
        assert make_engine().validate_answer(fd, 50).valid

    def test_max_fails_above_range(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.MAX, value=100)])
        assert not make_engine().validate_answer(fd, 101).valid

    def test_min_length_passes(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.MIN_LENGTH, value=3)],
        )
        assert make_engine().validate_answer(fd, "hello").valid

    def test_min_length_fails(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.MIN_LENGTH, value=10)],
        )
        assert not make_engine().validate_answer(fd, "hi").valid

    def test_max_length_fails(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.MAX_LENGTH, value=3)],
        )
        assert not make_engine().validate_answer(fd, "toolong").valid

    def test_pattern_passes(self):
        fd = FieldDefinition(
            key="f", type=FieldType.EMAIL, label="L",
            validators=[ValidatorRule(type=ValidatorType.PATTERN, value=r".+@.+\..+")],
        )
        assert make_engine().validate_answer(fd, "a@b.com").valid

    def test_pattern_fails(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.PATTERN, value=r"^\d+$")],
        )
        assert not make_engine().validate_answer(fd, "abc").valid

    def test_pattern_invalid_regex_treated_as_failure(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.PATTERN, value=r"[invalid(")],
        )
        result = make_engine().validate_answer(fd, "anything")
        assert not result.valid

    def test_enum_member_passes(self):
        fd = FieldDefinition(
            key="f", type=FieldType.SELECT, label="L", options=["a", "b", "c"],
            validators=[ValidatorRule(type=ValidatorType.ENUM_MEMBER)],
        )
        assert make_engine().validate_answer(fd, "a").valid

    def test_enum_member_fails(self):
        fd = FieldDefinition(
            key="f", type=FieldType.SELECT, label="L", options=["a", "b"],
            validators=[ValidatorRule(type=ValidatorType.ENUM_MEMBER)],
        )
        assert not make_engine().validate_answer(fd, "z").valid

    def test_date_after_passes(self):
        fd = FieldDefinition(
            key="f", type=FieldType.DATE, label="L",
            validators=[ValidatorRule(type=ValidatorType.DATE_AFTER, value="2000-01-01")],
        )
        assert make_engine().validate_answer(fd, "2024-06-15").valid

    def test_date_after_fails(self):
        fd = FieldDefinition(
            key="f", type=FieldType.DATE, label="L",
            validators=[ValidatorRule(type=ValidatorType.DATE_AFTER, value="2030-01-01")],
        )
        assert not make_engine().validate_answer(fd, "2024-06-15").valid

    def test_integer_coercion_from_string(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.MIN, value=0)])
        assert make_engine().validate_answer(fd, "42").valid

    def test_boolean_coercion_from_string_true(self):
        fd = FieldDefinition(key="f", type=FieldType.BOOLEAN, label="L")
        result = make_engine().validate_answer(fd, "true")
        assert result.valid

    def test_boolean_coercion_invalid(self):
        fd = FieldDefinition(key="f", type=FieldType.BOOLEAN, label="L")
        result = make_engine().validate_answer(fd, "maybe")
        assert not result.valid

    def test_multiple_failures_all_returned(self):
        fd = FieldDefinition(
            key="f", type=FieldType.INTEGER, label="L",
            validators=[
                ValidatorRule(type=ValidatorType.MIN, value=10),
                ValidatorRule(type=ValidatorType.MAX, value=5),
            ],
        )
        result = make_engine().validate_answer(fd, 7)
        assert not result.valid
        assert len(result.errors) == 2

    def test_raise_on_failure(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.REQUIRED)],
        )
        with pytest.raises(FieldValidationError):
            make_engine().validate_answer(fd, "", raise_on_failure=True)


# ------------------------------------------------------------------
# Planner response validation
# ------------------------------------------------------------------


def make_add_response(field: FieldDefinition) -> PlannerResponse:
    return PlannerResponse(
        actions=[PlannerAction(action=ActionType.ADD, field_key=field.key)],
        fields=[field],
        rationale=["r"],
        completion_status=CompletionStatus.IN_PROGRESS,
    )


class TestPlannerResponseValidation:
    def test_valid_response_passes(self):
        fd = text_field("extra")
        state = make_state()
        result = make_engine().validate_planner_response(make_add_response(fd), state)
        assert result.valid

    def test_exceeds_max_fields_rejected(self):
        policy = PolicyConfig(max_fields=1)
        engine = ValidationEngine(policy)
        existing = text_field("existing")
        state = make_state({"existing": existing})
        new_field = text_field("new_one")
        result = engine.validate_planner_response(make_add_response(new_field), state)
        assert not result.valid
        assert any("max_fields" in e.reason for e in result.errors)

    def test_prohibited_topic_in_rationale_rejected(self):
        policy = PolicyConfig(prohibited_topics=["violence"])
        engine = ValidationEngine(policy)
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.COMPLETE)],
            fields=[],
            rationale=["Checking for violence in answers"],
            completion_status=CompletionStatus.COMPLETE,
        )
        result = engine.validate_planner_response(response, make_state())
        assert not result.valid

    def test_update_nonexistent_field_rejected(self):
        fd = text_field("ghost")
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.UPDATE, field_key="ghost")],
            fields=[fd],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        result = make_engine().validate_planner_response(response, make_state())
        assert not result.valid

    def test_add_duplicate_key_rejected(self):
        existing = text_field("dup")
        state = make_state({"dup": existing})
        response = make_add_response(text_field("dup"))
        result = make_engine().validate_planner_response(response, state)
        assert not result.valid

    def test_raise_on_failure(self):
        fd = text_field("ghost")
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.UPDATE, field_key="ghost")],
            fields=[fd],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        with pytest.raises(PlannerOutputRejected):
            make_engine().validate_planner_response(
                response, make_state(), raise_on_failure=True
            )
