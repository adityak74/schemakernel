from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemakernel.models import FieldDefinition


class EscalationCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    field_key: str
    trigger: str = Field(max_length=200)


class CompletionCriteria(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_fields_answered: Optional[list[str]] = None
    minimum_answered_count: Optional[int] = Field(default=None, ge=1)
    custom_description: Optional[str] = Field(default=None, max_length=500)


class ExceptionRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[A-Z0-9_]+$", max_length=60)
    description: str = Field(max_length=500)
    follow_up_fields: list[str] = Field(default_factory=list)


class PolicyConfig(BaseModel):
    model_config = ConfigDict(frozen=False, validate_assignment=True)

    baseline_questions: list[FieldDefinition] = Field(default_factory=list)
    glossary: dict[str, str] = Field(default_factory=dict)
    exception_rules: list[ExceptionRule] = Field(default_factory=list)
    prohibited_topics: list[str] = Field(default_factory=list)
    escalation_thresholds: list[EscalationCondition] = Field(default_factory=list)
    completion_criteria: CompletionCriteria = Field(
        default_factory=CompletionCriteria
    )
    reasoning_style: str = Field(default="balanced", max_length=500)
    max_fields: int = Field(default=20, ge=1, le=100)
    max_turns: int = Field(default=10, ge=1, le=50)
    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = Field(default="claude-sonnet-4-6")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_retries: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def baseline_keys_unique(self) -> "PolicyConfig":
        keys = [f.key for f in self.baseline_questions]
        if len(keys) != len(set(keys)):
            raise ValueError("baseline_questions contains duplicate field keys")
        return self
