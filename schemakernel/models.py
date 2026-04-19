from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    TEXTAREA = "textarea"


class ValidatorType(str, Enum):
    REQUIRED = "required"
    MIN = "min"
    MAX = "max"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    ENUM_MEMBER = "enum_member"
    POSITIVE = "positive"
    NON_NEGATIVE = "non_negative"
    DATE_AFTER = "date_after"
    DATE_BEFORE = "date_before"


class ActionType(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    REQUIRE = "require"
    HIDE = "hide"
    SHOW = "show"
    REORDER = "reorder"
    COMPLETE = "complete"
    ESCALATE = "escalate"


class CompletionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    NEEDS_CLARIFICATION = "needs_clarification"
    COMPLETE = "complete"
    ESCALATE = "escalate"


class WorkflowStage(str, Enum):
    INITIALIZED = "initialized"
    COLLECTING = "collecting"
    CLARIFYING = "clarifying"
    COMPLETE = "complete"
    ESCALATED = "escalated"


class ConditionOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    IS_EMPTY = "is_empty"
    NOT_EMPTY = "not_empty"


class ValidatorRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: ValidatorType
    value: Optional[Union[str, int, float, bool]] = None
    message: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def value_required_for_parameterized(self) -> "ValidatorRule":
        parameterized = {
            ValidatorType.MIN,
            ValidatorType.MAX,
            ValidatorType.MIN_LENGTH,
            ValidatorType.MAX_LENGTH,
            ValidatorType.PATTERN,
            ValidatorType.DATE_AFTER,
            ValidatorType.DATE_BEFORE,
        }
        if self.type in parameterized and self.value is None:
            raise ValueError(f"ValidatorRule type '{self.type}' requires a value")
        return self


class Condition(BaseModel):
    model_config = ConfigDict(frozen=True)

    field_key: str
    operator: ConditionOperator
    value: Optional[Union[str, int, float, bool, list]] = None


class ConditionalLogic(BaseModel):
    model_config = ConfigDict(frozen=True)

    combinator: Literal["and", "or"] = "and"
    conditions: list[Condition] = Field(min_length=1)


_FORBIDDEN_UI_PATTERNS = frozenset(["__", "exec", "eval", "import", "<script", "javascript:"])


class FieldDefinition(BaseModel):
    model_config = ConfigDict(frozen=False, validate_assignment=True)

    key: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
    type: FieldType
    label: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    required: bool = False
    default: Optional[Any] = None
    validators: list[ValidatorRule] = Field(default_factory=list)
    ui_props: dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    visible_if: Optional[ConditionalLogic] = None
    ask_if_missing: bool = True
    follow_up_if: Optional[ConditionalLogic] = None
    priority: int = Field(default=100, ge=0, le=9999)
    options: Optional[list[str]] = None

    @model_validator(mode="after")
    def options_required_for_select(self) -> "FieldDefinition":
        if self.type in (FieldType.SELECT, FieldType.MULTISELECT):
            if not self.options:
                raise ValueError(
                    f"Field '{self.key}' of type '{self.type}' requires non-empty options"
                )
        return self

    @model_validator(mode="after")
    def ui_props_no_executable(self) -> "FieldDefinition":
        for k, v in self.ui_props.items():
            for pat in _FORBIDDEN_UI_PATTERNS:
                if pat in str(k).lower() or pat in str(v).lower():
                    raise ValueError(
                        f"ui_props contains forbidden pattern '{pat}' in key='{k}' value='{v}'"
                    )
        return self


class PlannerAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: ActionType
    field_key: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=0)
    reason_code: Optional[str] = Field(
        default=None,
        max_length=100,
        pattern=r"^[A-Z0-9_]+$",
    )

    @model_validator(mode="after")
    def field_key_required_for_field_actions(self) -> "PlannerAction":
        field_actions = {
            ActionType.ADD,
            ActionType.UPDATE,
            ActionType.REMOVE,
            ActionType.REQUIRE,
            ActionType.HIDE,
            ActionType.SHOW,
        }
        if self.action in field_actions and not self.field_key:
            raise ValueError(f"action '{self.action}' requires field_key")
        if self.action == ActionType.REORDER and self.position is None:
            raise ValueError("action 'reorder' requires position")
        return self


class PlannerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    actions: list[PlannerAction] = Field(min_length=1)
    fields: list[FieldDefinition] = Field(default_factory=list)
    rationale: list[str] = Field(min_length=1, max_length=20)
    completion_status: CompletionStatus
    next_prompt_context: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def add_update_actions_have_field_defs(self) -> "PlannerResponse":
        add_update_keys = {
            a.field_key
            for a in self.actions
            if a.action in (ActionType.ADD, ActionType.UPDATE)
        }
        defined_keys = {f.key for f in self.fields}
        missing = add_update_keys - defined_keys
        if missing:
            raise ValueError(
                f"PlannerResponse: actions reference undefined fields: {missing}"
            )
        return self

    @model_validator(mode="after")
    def complete_action_matches_status(self) -> "PlannerResponse":
        has_complete = any(a.action == ActionType.COMPLETE for a in self.actions)
        has_escalate = any(a.action == ActionType.ESCALATE for a in self.actions)
        if has_complete and self.completion_status != CompletionStatus.COMPLETE:
            raise ValueError("'complete' action requires completion_status='complete'")
        if has_escalate and self.completion_status != CompletionStatus.ESCALATE:
            raise ValueError("'escalate' action requires completion_status='escalate'")
        return self


# Sentinel visible_if that always evaluates to False (used by HIDE action)
ALWAYS_HIDDEN = ConditionalLogic(
    combinator="and",
    conditions=[
        Condition(
            field_key="__never__",
            operator=ConditionOperator.EQ,
            value="__never__",
        )
    ],
)


class SchemaState(BaseModel):
    model_config = ConfigDict(frozen=False)

    session_id: str
    fields: dict[str, FieldDefinition] = Field(default_factory=dict)
    field_order: list[str] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    stage: WorkflowStage = WorkflowStage.INITIALIZED
    turn_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class PlannerTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    turn: int
    raw_response: dict[str, Any]
    validated: bool
    rejection_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompletionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    status: CompletionStatus
    final_answers: dict[str, Any]
    final_schema: dict[str, Any]
    rationale: list[str]
    completed_at: datetime = Field(default_factory=datetime.utcnow)
