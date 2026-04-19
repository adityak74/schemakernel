from __future__ import annotations

import pytest
from pydantic import ValidationError

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
    ValidatorRule,
    ValidatorType,
)


class TestFieldDefinition:
    def test_all_field_types_valid(self):
        for ft in FieldType:
            opts = ["a", "b"] if ft in (FieldType.SELECT, FieldType.MULTISELECT) else None
            fd = FieldDefinition(key="f", type=ft, label="L", options=opts)
            assert fd.type == ft

    @pytest.mark.parametrize("key", ["my_field", "Field1", "_hidden", "a" * 64])
    def test_key_pattern_valid(self, key):
        fd = FieldDefinition(key=key, type=FieldType.TEXT, label="L")
        assert fd.key == key

    @pytest.mark.parametrize("key", ["1field", "my-field", "my.field", "a" * 65, ""])
    def test_key_pattern_invalid(self, key):
        with pytest.raises(ValidationError):
            FieldDefinition(key=key, type=FieldType.TEXT, label="L")

    def test_select_without_options_raises(self):
        with pytest.raises(ValidationError, match="requires non-empty options"):
            FieldDefinition(key="sel", type=FieldType.SELECT, label="L")

    def test_multiselect_without_options_raises(self):
        with pytest.raises(ValidationError, match="requires non-empty options"):
            FieldDefinition(key="ms", type=FieldType.MULTISELECT, label="L")

    def test_select_with_options_ok(self):
        fd = FieldDefinition(key="sel", type=FieldType.SELECT, label="L", options=["a", "b"])
        assert fd.options == ["a", "b"]

    @pytest.mark.parametrize(
        "bad_key,bad_value",
        [
            ("__class__", "something"),
            ("ok", "exec(code)"),
            ("ok", "<script>alert(1)</script>"),
            ("ok", "javascript:void(0)"),
        ],
    )
    def test_ui_props_forbidden_raises(self, bad_key, bad_value):
        with pytest.raises(ValidationError, match="forbidden pattern"):
            FieldDefinition(
                key="f", type=FieldType.TEXT, label="L", ui_props={bad_key: bad_value}
            )

    def test_ui_props_safe_values_ok(self):
        fd = FieldDefinition(
            key="f",
            type=FieldType.TEXT,
            label="L",
            ui_props={"placeholder": "Enter text", "rows": 3},
        )
        assert fd.ui_props["rows"] == 3


class TestValidatorRule:
    def test_parameterized_requires_value(self):
        for vt in (
            ValidatorType.MIN,
            ValidatorType.MAX,
            ValidatorType.MIN_LENGTH,
            ValidatorType.MAX_LENGTH,
            ValidatorType.PATTERN,
            ValidatorType.DATE_AFTER,
            ValidatorType.DATE_BEFORE,
        ):
            with pytest.raises(ValidationError, match="requires a value"):
                ValidatorRule(type=vt)

    def test_required_no_value_ok(self):
        vr = ValidatorRule(type=ValidatorType.REQUIRED)
        assert vr.value is None

    def test_positive_no_value_ok(self):
        vr = ValidatorRule(type=ValidatorType.POSITIVE)
        assert vr.value is None

    def test_min_with_value_ok(self):
        vr = ValidatorRule(type=ValidatorType.MIN, value=0)
        assert vr.value == 0


class TestPlannerAction:
    def test_add_requires_field_key(self):
        with pytest.raises(ValidationError, match="requires field_key"):
            PlannerAction(action=ActionType.ADD)

    def test_reorder_requires_position(self):
        with pytest.raises(ValidationError, match="requires position"):
            PlannerAction(action=ActionType.REORDER, field_key="f")

    def test_complete_no_field_key_ok(self):
        a = PlannerAction(action=ActionType.COMPLETE)
        assert a.field_key is None

    def test_reason_code_pattern(self):
        a = PlannerAction(action=ActionType.ADD, field_key="f", reason_code="MISSING_DOB")
        assert a.reason_code == "MISSING_DOB"

    def test_reason_code_invalid_pattern(self):
        with pytest.raises(ValidationError):
            PlannerAction(action=ActionType.ADD, field_key="f", reason_code="lower_case")


class TestPlannerResponse:
    def _make_field(self, key="extra"):
        return FieldDefinition(key=key, type=FieldType.TEXT, label="L")

    def test_add_without_field_def_raises(self):
        with pytest.raises(ValidationError, match="undefined fields"):
            PlannerResponse(
                actions=[PlannerAction(action=ActionType.ADD, field_key="missing")],
                fields=[],
                rationale=["r"],
                completion_status=CompletionStatus.IN_PROGRESS,
            )

    def test_complete_action_wrong_status_raises(self):
        fd = self._make_field()
        with pytest.raises(ValidationError, match="requires completion_status"):
            PlannerResponse(
                actions=[PlannerAction(action=ActionType.COMPLETE)],
                fields=[],
                rationale=["r"],
                completion_status=CompletionStatus.IN_PROGRESS,
            )

    def test_escalate_action_wrong_status_raises(self):
        with pytest.raises(ValidationError, match="requires completion_status"):
            PlannerResponse(
                actions=[PlannerAction(action=ActionType.ESCALATE)],
                fields=[],
                rationale=["r"],
                completion_status=CompletionStatus.IN_PROGRESS,
            )

    def test_valid_add_response(self):
        fd = self._make_field()
        r = PlannerResponse(
            actions=[PlannerAction(action=ActionType.ADD, field_key="extra")],
            fields=[fd],
            rationale=["Adding field"],
            completion_status=CompletionStatus.IN_PROGRESS,
        )
        assert r.completion_status == CompletionStatus.IN_PROGRESS

    def test_valid_complete_response(self):
        r = PlannerResponse(
            actions=[PlannerAction(action=ActionType.COMPLETE)],
            fields=[],
            rationale=["Done"],
            completion_status=CompletionStatus.COMPLETE,
        )
        assert r.completion_status == CompletionStatus.COMPLETE


class TestConditionalLogic:
    def test_empty_conditions_raises(self):
        with pytest.raises(ValidationError):
            ConditionalLogic(conditions=[])

    def test_valid_condition(self):
        c = Condition(field_key="age", operator=ConditionOperator.GT, value=18)
        logic = ConditionalLogic(conditions=[c])
        assert logic.combinator == "and"
