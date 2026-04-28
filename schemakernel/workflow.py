from __future__ import annotations

import json
import uuid
from typing import Any

from schemakernel.exceptions import (
    PlannerOutputRejected,
    SessionNotFound,
    TurnLimitExceeded,
)
from schemakernel.models import (
    ALWAYS_HIDDEN,
    ActionType,
    CompletionOutcome,
    CompletionStatus,
    ConditionalLogic,
    ConditionOperator,
    FieldDefinition,
    PlannerResponse,
    PlannerTrace,
    SchemaState,
    WorkflowStage,
)
from schemakernel.planner import PlannerClient
from schemakernel.policy import PolicyConfig
from schemakernel.store import InMemoryStore, StorageBackend
from schemakernel.validation import ValidationEngine, ValidationResult


class WorkflowStateMachine:
    def __init__(
        self,
        policy: PolicyConfig,
        store: StorageBackend,
        planner: PlannerClient,
        validator: ValidationEngine,
    ) -> None:
        self._policy = policy
        self._store = store
        self._planner = planner
        self._validator = validator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_session(self, session_id: str | None = None) -> SchemaState:
        sid = session_id or str(uuid.uuid4())
        state = SchemaState(session_id=sid)

        for fd in self._policy.baseline_questions:
            state.fields[fd.key] = fd.model_copy(deep=True)
            state.field_order.append(fd.key)

        state.stage = WorkflowStage.COLLECTING
        state.touch()
        self._store.save_state(state)
        return state.model_copy(deep=True)

    def submit_answer(
        self,
        session_id: str,
        field_key: str,
        value: Any,
        *,
        raise_on_failure: bool = False,
    ) -> ValidationResult:
        state = self._store.load_state(session_id)

        if field_key not in state.fields:
            from schemakernel.exceptions import FieldValidationError
            err = FieldValidationError(
                key=field_key,
                reason=f"Field '{field_key}' does not exist in schema",
            )
            result = ValidationResult(valid=False, errors=[err])
            if raise_on_failure:
                raise err
            return result

        field = state.fields[field_key]
        result = self._validator.validate_answer(field, value, raise_on_failure=raise_on_failure)

        if result.valid:
            state.answers[field_key] = value
            state.audit_log.append(
                {"event": "answer_submitted", "field_key": field_key, "value": value}
            )
            state.touch()
            self._store.save_state(state)

        return result

    def run_planner_turn(self, session_id: str) -> SchemaState:
        state = self._store.load_state(session_id)

        if state.turn_count >= self._policy.max_turns:
            raise TurnLimitExceeded(
                f"Session '{session_id}' reached max_turns={self._policy.max_turns}"
            )

        system_prompt = self._build_system_prompt(state)
        messages = self._build_messages(state)

        response = self._planner.call(messages, system_prompt)

        raw = json.loads(response.model_dump_json())
        trace = PlannerTrace(
            session_id=session_id,
            turn=state.turn_count,
            raw_response=raw,
            validated=False,
        )

        val_result = self._validator.validate_planner_response(response, state)

        if not val_result.valid:
            rejection = "; ".join(e.reason for e in val_result.errors)
            trace = PlannerTrace(
                session_id=session_id,
                turn=state.turn_count,
                raw_response=raw,
                validated=False,
                rejection_reason=rejection,
            )
            self._store.save_trace(trace)
            raise PlannerOutputRejected(f"Planner response rejected: {rejection}")

        trace = PlannerTrace(
            session_id=session_id,
            turn=state.turn_count,
            raw_response=raw,
            validated=True,
        )
        self._store.save_trace(trace)

        self._apply_actions(state, response)
        state.turn_count += 1
        state.audit_log.append(
            {
                "event": "planner_turn",
                "turn": state.turn_count,
                "completion_status": response.completion_status.value,
                "rationale": response.rationale,
            }
        )
        state.touch()

        if response.completion_status in (
            CompletionStatus.COMPLETE,
            CompletionStatus.ESCALATE,
        ):
            outcome = CompletionOutcome(
                session_id=session_id,
                status=response.completion_status,
                final_answers=dict(state.answers),
                final_schema={k: v.model_dump() for k, v in state.fields.items()},
                rationale=response.rationale,
            )
            self._store.save_outcome(outcome)

        self._store.save_state(state)
        return state.model_copy(deep=True)

    def get_next_fields(self, session_id: str) -> list[FieldDefinition]:
        state = self._store.load_state(session_id)
        result: list[FieldDefinition] = []

        for key in state.field_order:
            fd = state.fields.get(key)
            if fd is None:
                continue
            if not fd.ask_if_missing:
                continue
            if key in state.answers:
                continue
            if fd.visible_if is not None:
                if not self._evaluate_condition(fd.visible_if, state.answers):
                    continue
            result.append(fd)

        result.sort(key=lambda f: f.priority)
        return result

    def get_state(self, session_id: str) -> SchemaState:
        return self._store.load_state(session_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self, state: SchemaState) -> str:
        p = self._policy
        lines: list[str] = [
            "You are a form planning assistant for SchemaKernel.",
            f"Reasoning style: {p.reasoning_style}",
            "",
            "Your job is to decide which fields to add, update, or finalize based on the",
            "current schema and the answers collected so far.",
            "You MUST return a valid PlannerResponse. Do not generate HTML, CSS, or executable code.",
            "",
        ]

        if p.glossary:
            lines.append("## Glossary")
            for term, definition in p.glossary.items():
                lines.append(f"- {term}: {definition}")
            lines.append("")

        if p.prohibited_topics:
            lines.append("## Prohibited Topics")
            lines.append("You must NOT reference these topics in any field or rationale:")
            for topic in p.prohibited_topics:
                lines.append(f"- {topic}")
            lines.append("")

        if p.exception_rules:
            lines.append("## Exception Rules")
            for rule in p.exception_rules:
                lines.append(f"- [{rule.name}] {rule.description}")
            lines.append("")

        criteria = p.completion_criteria
        if criteria.required_fields_answered or criteria.minimum_answered_count or criteria.custom_description:
            lines.append("## Completion Criteria")
            if criteria.required_fields_answered:
                lines.append(f"- Required fields answered: {criteria.required_fields_answered}")
            if criteria.minimum_answered_count:
                lines.append(f"- Minimum answered count: {criteria.minimum_answered_count}")
            if criteria.custom_description:
                lines.append(f"- {criteria.custom_description}")
            lines.append("")

        lines.append("## Current Schema")
        if state.fields:
            for key in state.field_order:
                fd = state.fields.get(key)
                if fd is None:
                    continue
                answered = "answered" if key in state.answers else "not answered"
                lines.append(
                    f"- {key} ({fd.type.value}, required={fd.required}, {answered}): {fd.label}"
                )
        else:
            lines.append("(no fields yet)")
        lines.append("")

        lines.append(f"Max fields allowed: {p.max_fields}")
        lines.append(f"Current turn: {state.turn_count + 1} / {p.max_turns}")

        return "\n".join(lines)

    def _build_messages(self, state: SchemaState) -> list[dict]:
        messages: list[dict] = []

        answers_text = json.dumps(state.answers, default=str, indent=2)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Current answers:\n```json\n{answers_text}\n```\n\n"
                    "Based on the policy and the answers above, decide what to do next. "
                    "Return a PlannerResponse."
                ),
            }
        )
        return messages

    def _apply_actions(self, state: SchemaState, response: PlannerResponse) -> None:
        field_map = {f.key: f for f in response.fields}

        for action in response.actions:
            if action.action == ActionType.ADD:
                key = action.field_key
                fd = field_map[key]
                state.fields[key] = fd.model_copy(deep=True)
                if key not in state.field_order:
                    state.field_order.append(key)

            elif action.action == ActionType.UPDATE:
                key = action.field_key
                fd = field_map[key]
                state.fields[key] = fd.model_copy(deep=True)

            elif action.action == ActionType.REMOVE:
                key = action.field_key
                state.fields.pop(key, None)
                if key in state.field_order:
                    state.field_order.remove(key)
                state.answers.pop(key, None)

            elif action.action == ActionType.REQUIRE:
                key = action.field_key
                if key in state.fields:
                    state.fields[key].required = True

            elif action.action == ActionType.HIDE:
                key = action.field_key
                if key in state.fields:
                    state.fields[key].visible_if = ALWAYS_HIDDEN

            elif action.action == ActionType.SHOW:
                key = action.field_key
                if key in state.fields:
                    state.fields[key].visible_if = None

            elif action.action == ActionType.REORDER:
                key = action.field_key
                if key in state.field_order and action.position is not None:
                    state.field_order.remove(key)
                    pos = min(action.position, len(state.field_order))
                    state.field_order.insert(pos, key)

            elif action.action == ActionType.COMPLETE:
                state.stage = WorkflowStage.COMPLETE

            elif action.action == ActionType.ESCALATE:
                state.stage = WorkflowStage.ESCALATED

    def _evaluate_condition(
        self, logic: ConditionalLogic, answers: dict[str, Any]
    ) -> bool:
        results = [self._eval_single(c, answers) for c in logic.conditions]
        if logic.combinator == "and":
            return all(results)
        return any(results)

    def _eval_single(self, condition, answers: dict[str, Any]) -> bool:
        value = answers.get(condition.field_key)
        op = condition.operator
        cv = condition.value

        if op == ConditionOperator.IS_EMPTY:
            return value is None or value == ""
        if op == ConditionOperator.NOT_EMPTY:
            return value is not None and value != ""
        if op == ConditionOperator.EQ:
            return value == cv
        if op == ConditionOperator.NEQ:
            return value != cv
        if op == ConditionOperator.IN:
            return isinstance(cv, list) and value in cv
        if op == ConditionOperator.NOT_IN:
            return isinstance(cv, list) and value not in cv

        # Numeric comparisons
        try:
            fv = float(value)  # type: ignore[arg-type]
            fc = float(cv)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False

        if op == ConditionOperator.GT:
            return fv > fc
        if op == ConditionOperator.GTE:
            return fv >= fc
        if op == ConditionOperator.LT:
            return fv < fc
        if op == ConditionOperator.LTE:
            return fv <= fc

        return False


def create_workflow(
    policy: PolicyConfig | None = None,
    store: StorageBackend | None = None,
    planner: Any | None = None,
    validator: ValidationEngine | None = None,
) -> WorkflowStateMachine:
    """
    Factory function to create a WorkflowStateMachine with sensible defaults.
    """
    p = policy or PolicyConfig()
    s = store or InMemoryStore()
    v = validator or ValidationEngine(p)
    pl = planner or PlannerClient(p)
    return WorkflowStateMachine(p, s, pl, v)
