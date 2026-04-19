from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from schemakernel.exceptions import FieldValidationError, PlannerOutputRejected
from schemakernel.models import (
    ActionType,
    FieldDefinition,
    FieldType,
    PlannerResponse,
    SchemaState,
    ValidatorType,
)
from schemakernel.policy import PolicyConfig

_ALLOWED_ACTION_TYPES: frozenset[str] = frozenset(a.value for a in ActionType)
_ALLOWED_FIELD_TYPES: frozenset[str] = frozenset(f.value for f in FieldType)
_ALLOWED_VALIDATOR_TYPES: frozenset[str] = frozenset(v.value for v in ValidatorType)

_FORBIDDEN_UI_PATTERNS = frozenset(["__", "exec", "eval", "import", "<script", "javascript:"])


@dataclass
class ValidationResult:
    valid: bool
    errors: list[FieldValidationError] = field(default_factory=list)


class ValidationEngine:
    def __init__(self, policy: PolicyConfig) -> None:
        self._policy = policy

    # ------------------------------------------------------------------
    # Job A: Planner output validation
    # ------------------------------------------------------------------

    def validate_planner_response(
        self,
        response: PlannerResponse,
        current_state: SchemaState,
        *,
        raise_on_failure: bool = False,
    ) -> ValidationResult:
        errors: list[FieldValidationError] = []

        # 1. Allowlist: action types
        for action in response.actions:
            if action.action.value not in _ALLOWED_ACTION_TYPES:
                errors.append(
                    FieldValidationError(
                        key="_action",
                        reason=f"Unknown action type '{action.action}'",
                    )
                )

        # 2. Allowlist: field types
        for fd in response.fields:
            if fd.type.value not in _ALLOWED_FIELD_TYPES:
                errors.append(
                    FieldValidationError(
                        key=fd.key,
                        reason=f"Unknown field type '{fd.type}'",
                    )
                )

        # 3. Allowlist: validator types
        for fd in response.fields:
            for vr in fd.validators:
                if vr.type.value not in _ALLOWED_VALIDATOR_TYPES:
                    errors.append(
                        FieldValidationError(
                            key=fd.key,
                            reason=f"Unknown validator type '{vr.type}'",
                        )
                    )

        # 4. Safety: ui_props forbidden patterns (defense-in-depth)
        for fd in response.fields:
            for k, v in fd.ui_props.items():
                for pat in _FORBIDDEN_UI_PATTERNS:
                    if pat in str(k).lower() or pat in str(v).lower():
                        errors.append(
                            FieldValidationError(
                                key=fd.key,
                                reason=f"ui_props contains forbidden pattern '{pat}'",
                            )
                        )

        # 5. Policy: max_fields check
        add_keys = {a.field_key for a in response.actions if a.action == ActionType.ADD}
        remove_keys = {a.field_key for a in response.actions if a.action == ActionType.REMOVE}
        projected_count = len(current_state.fields) + len(add_keys) - len(remove_keys)
        if projected_count > self._policy.max_fields:
            errors.append(
                FieldValidationError(
                    key="_schema",
                    reason=(
                        f"Schema would have {projected_count} fields, "
                        f"exceeding max_fields={self._policy.max_fields}"
                    ),
                )
            )

        # 6. Policy: prohibited topics in field keys/labels and rationale/context
        errors.extend(self._check_prohibited_content(response))

        # 7. Cross-reference: ADD must not duplicate existing keys
        for action in response.actions:
            if action.action == ActionType.ADD and action.field_key in current_state.fields:
                errors.append(
                    FieldValidationError(
                        key=action.field_key or "_action",
                        reason=f"ADD action targets already-existing field '{action.field_key}'",
                    )
                )

        # 8. Cross-reference: UPDATE/REMOVE/REQUIRE/HIDE/SHOW must target existing keys
        mutate_actions = {
            ActionType.UPDATE,
            ActionType.REMOVE,
            ActionType.REQUIRE,
            ActionType.HIDE,
            ActionType.SHOW,
            ActionType.REORDER,
        }
        for action in response.actions:
            if action.action in mutate_actions and action.field_key:
                if action.field_key not in current_state.fields:
                    errors.append(
                        FieldValidationError(
                            key=action.field_key,
                            reason=f"action '{action.action}' targets non-existent field '{action.field_key}'",
                        )
                    )

        result = ValidationResult(valid=len(errors) == 0, errors=errors)
        if not result.valid and raise_on_failure:
            raise PlannerOutputRejected(
                f"Planner response rejected: {'; '.join(e.reason for e in errors)}"
            )
        return result

    def _check_prohibited_content(self, response: PlannerResponse) -> list[FieldValidationError]:
        errors: list[FieldValidationError] = []
        if not self._policy.prohibited_topics:
            return errors

        topics = [t.lower() for t in self._policy.prohibited_topics]

        # Check field keys and labels
        for fd in response.fields:
            combined = f"{fd.key} {fd.label or ''} {fd.description or ''}".lower()
            for topic in topics:
                if topic in combined:
                    errors.append(
                        FieldValidationError(
                            key=fd.key,
                            reason=f"Field references prohibited topic '{topic}'",
                        )
                    )
                    break

        # Check rationale and next_prompt_context
        for text in response.rationale:
            tl = text.lower()
            for topic in topics:
                if topic in tl:
                    errors.append(
                        FieldValidationError(
                            key="_rationale",
                            reason=f"Rationale references prohibited topic '{topic}'",
                        )
                    )
                    break

        if response.next_prompt_context:
            npc = response.next_prompt_context.lower()
            for topic in topics:
                if topic in npc:
                    errors.append(
                        FieldValidationError(
                            key="_next_prompt_context",
                            reason=f"next_prompt_context references prohibited topic '{topic}'",
                        )
                    )
                    break

        return errors

    # ------------------------------------------------------------------
    # Job B: Answer validation
    # ------------------------------------------------------------------

    def validate_answer(
        self,
        field: FieldDefinition,
        value: Any,
        *,
        raise_on_failure: bool = False,
    ) -> ValidationResult:
        errors: list[FieldValidationError] = []

        # Type coercion
        coerced, coerce_error = self._coerce(field, value)
        if coerce_error:
            errors.append(FieldValidationError(key=field.key, reason=coerce_error, value=value))
            result = ValidationResult(valid=False, errors=errors)
            if raise_on_failure:
                raise errors[0]
            return result

        # Per-rule checks
        for rule in field.validators:
            error = self._check_rule(field, rule, coerced)
            if error:
                errors.append(error)

        result = ValidationResult(valid=len(errors) == 0, errors=errors)
        if not result.valid and raise_on_failure:
            raise errors[0]
        return result

    def _coerce(self, field: FieldDefinition, value: Any) -> tuple[Any, str | None]:
        if value is None:
            return None, None

        try:
            if field.type == FieldType.INTEGER:
                return int(value), None
            if field.type == FieldType.NUMBER:
                return float(value), None
            if field.type == FieldType.BOOLEAN:
                if isinstance(value, bool):
                    return value, None
                sv = str(value).lower().strip()
                if sv in ("true", "1", "yes"):
                    return True, None
                if sv in ("false", "0", "no"):
                    return False, None
                return None, f"Cannot coerce '{value}' to boolean"
            if field.type == FieldType.DATE:
                from dateutil import parser as dp
                return dp.parse(str(value)).date(), None
            if field.type == FieldType.DATETIME:
                from dateutil import parser as dp
                return dp.parse(str(value)), None
        except (ValueError, TypeError, OverflowError) as exc:
            return None, f"Type coercion failed for type '{field.type}': {exc}"

        return value, None

    def _check_rule(
        self, field: FieldDefinition, rule, coerced: Any
    ) -> FieldValidationError | None:
        key = field.key
        msg = rule.message

        def err(default: str) -> FieldValidationError:
            return FieldValidationError(key=key, reason=msg or default, value=coerced)

        if rule.type == ValidatorType.REQUIRED:
            if coerced is None or coerced == "":
                return err("This field is required")

        elif rule.type == ValidatorType.MIN:
            if coerced is not None:
                try:
                    if float(coerced) < float(rule.value):
                        return err(f"Value must be >= {rule.value}")
                except (TypeError, ValueError):
                    return err(f"Cannot compare value to min={rule.value}")

        elif rule.type == ValidatorType.MAX:
            if coerced is not None:
                try:
                    if float(coerced) > float(rule.value):
                        return err(f"Value must be <= {rule.value}")
                except (TypeError, ValueError):
                    return err(f"Cannot compare value to max={rule.value}")

        elif rule.type == ValidatorType.MIN_LENGTH:
            if coerced is not None:
                if len(str(coerced)) < int(rule.value):
                    return err(f"Length must be >= {rule.value}")

        elif rule.type == ValidatorType.MAX_LENGTH:
            if coerced is not None:
                if len(str(coerced)) > int(rule.value):
                    return err(f"Length must be <= {rule.value}")

        elif rule.type == ValidatorType.PATTERN:
            if coerced is not None:
                try:
                    if not re.fullmatch(str(rule.value), str(coerced)):
                        return err(f"Value does not match pattern '{rule.value}'")
                except re.error:
                    return err(f"Invalid regex pattern '{rule.value}'")

        elif rule.type == ValidatorType.ENUM_MEMBER:
            if coerced is not None and field.options:
                if str(coerced) not in field.options:
                    return err(f"Value must be one of {field.options}")

        elif rule.type == ValidatorType.POSITIVE:
            if coerced is not None:
                try:
                    if float(coerced) <= 0:
                        return err("Value must be positive (> 0)")
                except (TypeError, ValueError):
                    return err("Cannot verify positivity of value")

        elif rule.type == ValidatorType.NON_NEGATIVE:
            if coerced is not None:
                try:
                    if float(coerced) < 0:
                        return err("Value must be non-negative (>= 0)")
                except (TypeError, ValueError):
                    return err("Cannot verify non-negativity of value")

        elif rule.type == ValidatorType.DATE_AFTER:
            if coerced is not None:
                try:
                    from dateutil import parser as dp
                    threshold = dp.parse(str(rule.value)).date()
                    coerced_date = coerced if hasattr(coerced, "year") else dp.parse(str(coerced)).date()
                    if coerced_date <= threshold:
                        return err(f"Date must be after {rule.value}")
                except (ValueError, TypeError):
                    return err(f"Cannot compare date to threshold '{rule.value}'")

        elif rule.type == ValidatorType.DATE_BEFORE:
            if coerced is not None:
                try:
                    from dateutil import parser as dp
                    threshold = dp.parse(str(rule.value)).date()
                    coerced_date = coerced if hasattr(coerced, "year") else dp.parse(str(coerced)).date()
                    if coerced_date >= threshold:
                        return err(f"Date must be before {rule.value}")
                except (ValueError, TypeError):
                    return err(f"Cannot compare date to threshold '{rule.value}'")

        return None
