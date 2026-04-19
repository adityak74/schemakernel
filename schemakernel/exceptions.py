from __future__ import annotations

from typing import Any


class SchemakernelError(Exception):
    pass


# Planner layer
class PlannerError(SchemakernelError):
    pass


class PlannerResponseError(PlannerError):
    pass


class PlannerRetryExhausted(PlannerError):
    pass


# Validation layer
class ValidationError(SchemakernelError):
    pass


class FieldValidationError(ValidationError):
    def __init__(self, key: str, reason: str, value: Any = None) -> None:
        self.key = key
        self.reason = reason
        self.value = value
        super().__init__(f"Field '{key}': {reason}")


class PolicyViolationError(ValidationError):
    pass


class PlannerOutputRejected(ValidationError):
    pass


# Workflow layer
class WorkflowError(SchemakernelError):
    pass


class TurnLimitExceeded(WorkflowError):
    pass


class SessionNotFound(WorkflowError):
    pass


class InvalidTransition(WorkflowError):
    pass
