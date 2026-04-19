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

    def test_raise_on_failure_coercion_error(self):
        fd = FieldDefinition(key="f", type=FieldType.INTEGER, label="L")
        with pytest.raises(FieldValidationError):
            make_engine().validate_answer(fd, "not-a-number", raise_on_failure=True)

    def test_number_coercion(self):
        fd = FieldDefinition(key="f", type=FieldType.NUMBER, label="L")
        result = make_engine().validate_answer(fd, "3.14")
        assert result.valid

    def test_boolean_coercion_from_bool(self):
        fd = FieldDefinition(key="f", type=FieldType.BOOLEAN, label="L")
        assert make_engine().validate_answer(fd, True).valid
        assert make_engine().validate_answer(fd, False).valid

    def test_boolean_coercion_yes_no(self):
        fd = FieldDefinition(key="f", type=FieldType.BOOLEAN, label="L")
        assert make_engine().validate_answer(fd, "yes").valid
        assert make_engine().validate_answer(fd, "no").valid
        assert make_engine().validate_answer(fd, "1").valid
        assert make_engine().validate_answer(fd, 0).valid

    def test_date_coercion(self):
        fd = FieldDefinition(key="f", type=FieldType.DATE, label="L")
        result = make_engine().validate_answer(fd, "2024-01-01")
        assert result.valid

    def test_datetime_coercion(self):
        fd = FieldDefinition(key="f", type=FieldType.DATETIME, label="L")
        result = make_engine().validate_answer(fd, "2024-01-01T12:00:00")
        assert result.valid

    def test_coercion_failure_returns_error(self):
        fd = FieldDefinition(key="f", type=FieldType.INTEGER, label="L")
        result = make_engine().validate_answer(fd, "not-a-number")
        assert not result.valid
        assert "Type coercion failed" in result.errors[0].reason

    def test_positive_validator(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.POSITIVE)])
        assert make_engine().validate_answer(fd, 1).valid
        assert not make_engine().validate_answer(fd, 0).valid
        assert not make_engine().validate_answer(fd, -1).valid

    def test_positive_validator_fails_non_numeric(self):
        fd = FieldDefinition(key="f", type=FieldType.TEXT, label="L", validators=[ValidatorRule(type=ValidatorType.POSITIVE)])
        result = make_engine().validate_answer(fd, "abc")
        assert not result.valid
        assert "Cannot verify positivity" in result.errors[0].reason

    def test_non_negative_validator(self):
        fd = int_field(validators=[ValidatorRule(type=ValidatorType.NON_NEGATIVE)])
        assert make_engine().validate_answer(fd, 0).valid
        assert make_engine().validate_answer(fd, 1).valid
        assert not make_engine().validate_answer(fd, -1).valid

    def test_non_negative_validator_fails_non_numeric(self):
        fd = FieldDefinition(key="f", type=FieldType.TEXT, label="L", validators=[ValidatorRule(type=ValidatorType.NON_NEGATIVE)])
        result = make_engine().validate_answer(fd, "abc")
        assert not result.valid
        assert "Cannot verify non-negativity" in result.errors[0].reason

    def test_date_before_validator(self):
        fd = FieldDefinition(
            key="f", type=FieldType.DATE, label="L",
            validators=[ValidatorRule(type=ValidatorType.DATE_BEFORE, value="2000-01-01")],
        )
        assert make_engine().validate_answer(fd, "1999-12-31").valid
        assert not make_engine().validate_answer(fd, "2000-01-01").valid

    def test_date_before_validator_fails_invalid_threshold(self):
        # Bypass validation of ValidatorRule to provide bad threshold
        vr = ValidatorRule.model_construct(type=ValidatorType.DATE_BEFORE, value="not-a-date")
        fd = FieldDefinition(
            key="f", type=FieldType.DATE, label="L",
            validators=[vr],
        )
        result = make_engine().validate_answer(fd, "2024-01-01")
        assert not result.valid
        assert "Cannot compare date to threshold" in result.errors[0].reason

    def test_date_after_validator_fails_invalid_threshold(self):
        # Bypass validation of ValidatorRule to provide bad threshold
        vr = ValidatorRule.model_construct(type=ValidatorType.DATE_AFTER, value="not-a-date")
        fd = FieldDefinition(
            key="f", type=FieldType.DATE, label="L",
            validators=[vr],
        )
        result = make_engine().validate_answer(fd, "2024-01-01")
        assert not result.valid
        assert "Cannot compare date to threshold" in result.errors[0].reason

    def test_comparison_failure_non_numeric(self):
        fd = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.MIN, value=10)],
        )
        result = make_engine().validate_answer(fd, "abc")
        assert not result.valid
        assert "Cannot compare value" in result.errors[0].reason

        fd2 = FieldDefinition(
            key="f", type=FieldType.TEXT, label="L",
            validators=[ValidatorRule(type=ValidatorType.MAX, value=10)],
        )
        result2 = make_engine().validate_answer(fd2, "abc")
        assert not result2.valid
        assert "Cannot compare value" in result2.errors[0].reason

    def test_enum_member_empty_options_handled(self):
        fd = FieldDefinition.model_construct(
            key="f", type=FieldType.SELECT, label="L", options=None,
            validators=[ValidatorRule(type=ValidatorType.ENUM_MEMBER)]
        )
        result = make_engine().validate_answer(fd, "anything")
        assert result.valid


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

    def test_unknown_action_type(self):
        # Using model_construct to bypass Pydantic validation
        from unittest.mock import MagicMock
        bad_action = MagicMock()
        bad_action.action.value = "EXPLODE"
        bad_action.field_key = "f"
        
        response = PlannerResponse.model_construct(
            actions=[bad_action],
            fields=[],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS
        )
        result = make_engine().validate_planner_response(response, make_state())
        assert not result.valid
        assert any("Unknown action type" in e.reason for e in result.errors)

    def test_unknown_field_type(self):
        from unittest.mock import MagicMock
        bad_field = MagicMock()
        bad_field.key = "f"
        bad_field.type.value = "MAGIC"
        bad_field.validators = []
        bad_field.ui_props = {}
        bad_field.label = "L"
        bad_field.description = None
        
        response = PlannerResponse.model_construct(
            actions=[PlannerAction(action=ActionType.ADD, field_key="f")],
            fields=[bad_field],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS
        )
        result = make_engine().validate_planner_response(response, make_state())
        assert not result.valid
        assert any("Unknown field type" in e.reason for e in result.errors)

    def test_unknown_validator_type(self):
        from unittest.mock import MagicMock
        fd = FieldDefinition.model_construct(
            key="f",
            type=FieldType.TEXT,
            label="L",
            validators=[MagicMock(type=MagicMock(value="SUPER_VALIDATE"))]
        )
        
        response = PlannerResponse.model_construct(
            actions=[PlannerAction(action=ActionType.ADD, field_key="f")],
            fields=[fd],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS
        )
        result = make_engine().validate_planner_response(response, make_state())
        assert not result.valid
        assert any("Unknown validator type" in e.reason for e in result.errors)

    def test_ui_props_forbidden_patterns(self):
        # Bypass pydantic validation for FieldDefinition
        fd = FieldDefinition.model_construct(
            key="f", type=FieldType.TEXT, label="L", ui_props={"onclick": "javascript:alert(1)"},
            validators=[]
        )
        
        response = PlannerResponse.model_construct(
            actions=[PlannerAction(action=ActionType.ADD, field_key="f")],
            fields=[fd],
            rationale=["r"],
            completion_status=CompletionStatus.IN_PROGRESS
        )
        result = make_engine().validate_planner_response(response, make_state())
        assert not result.valid
        assert any("forbidden pattern" in e.reason for e in result.errors)

    def test_prohibited_topic_in_field_definition(self):
        policy = PolicyConfig(prohibited_topics=["secret"])
        engine = ValidationEngine(policy)
        
        # Topic in key
        fd1 = FieldDefinition(key="my_secret", type=FieldType.TEXT, label="L")
        result = engine.validate_planner_response(make_add_response(fd1), make_state())
        assert not result.valid
        assert "prohibited topic" in result.errors[0].reason

        # Topic in label
        fd2 = FieldDefinition(key="f", type=FieldType.TEXT, label="Top Secret")
        result = engine.validate_planner_response(make_add_response(fd2), make_state())
        assert not result.valid

        # Topic in description
        fd3 = FieldDefinition(key="f", type=FieldType.TEXT, label="L", description="A secret field")
        result = engine.validate_planner_response(make_add_response(fd3), make_state())
        assert not result.valid

    def test_prohibited_topic_in_next_prompt_context(self):
        policy = PolicyConfig(prohibited_topics=["forbidden"])
        engine = ValidationEngine(policy)
        
        response = PlannerResponse(
            actions=[PlannerAction(action=ActionType.COMPLETE)],
            fields=[],
            rationale=["r"],
            completion_status=CompletionStatus.COMPLETE,
            next_prompt_context="This contains forbidden info"
        )
        result = engine.validate_planner_response(response, make_state())
        assert not result.valid
        assert result.errors[0].key == "_next_prompt_context"
