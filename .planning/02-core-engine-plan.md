# SchemaKernel Phase 1 — Core Engine Implementation Plan

## Context

The repository is a greenfield Python project. Phase 1 delivers the core engine: canonical schema models, typed planner contract (via Instructor), deterministic validation engine, policy configuration, and in-memory storage. The LLM acts as a constrained planner; all execution is deterministic.

Branch: `claude/schemakernel-core-HlR2o`

---

## File Structure

```
schemakernel/
├── .planning/
│   ├── 01-product-requirements.md   # PRD
│   └── 02-core-engine-plan.md       # this file
├── pyproject.toml
├── .gitignore
├── README.md
├── schemakernel/
│   ├── __init__.py          # public API surface
│   ├── exceptions.py        # all custom exceptions
│   ├── models.py            # all Pydantic models
│   ├── policy.py            # PolicyConfig
│   ├── validation.py        # ValidationEngine
│   ├── planner.py           # PlannerClient (Instructor-based)
│   ├── store.py             # StorageBackend ABC + InMemoryStore
│   └── workflow.py          # WorkflowStateMachine + create_workflow()
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_validation.py
    ├── test_planner.py
    ├── test_store.py
    └── test_workflow.py
```

---

## Key Models

### Enumerations

- `FieldType`: text, number, integer, boolean, date, datetime, select, multiselect, email, url, phone, textarea
- `ValidatorType`: required, min, max, min_length, max_length, pattern, enum_member, positive, non_negative, date_after, date_before
- `ActionType`: add, update, remove, require, hide, show, reorder, complete, escalate
- `CompletionStatus`: in_progress, needs_clarification, complete, escalate
- `WorkflowStage`: initialized, collecting, clarifying, complete, escalated
- `ConditionOperator`: eq, neq, gt, gte, lt, lte, in, not_in, is_empty, not_empty

### `FieldDefinition`
Key validation constraints:
- `key` pattern: `^[a-zA-Z_][a-zA-Z0-9_]{0,63}$`
- `ui_props` values: `str|int|float|bool` only (no executable content)
- `options` required for select/multiselect

### `PlannerResponse`
- `actions`: min 1 item
- `rationale`: 1–20 strings
- `next_prompt_context`: max 2000 chars
- Cross-validators: add/update actions must have matching FieldDefinition; complete/escalate action must match completion_status

### `SchemaState`
Mutable session state: fields dict, field_order, answers, stage, turn_count, audit_log.

---

## Safety Architecture

Two independent enforcement layers:
1. **Instructor + Pydantic** at the LLM API boundary (cross-validators trigger Instructor retries)
2. **ValidationEngine allowlists** (`frozenset`) before any state mutation

No `eval`, no callable validators, no raw HTML. `ui_props` values structurally limited to scalars.

---

## Workflow State Transitions

```
INITIALIZED → [start_session] → COLLECTING
COLLECTING/CLARIFYING → [run_planner_turn] → COLLECTING | CLARIFYING | COMPLETE | ESCALATED
```

---

## Verification

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=schemakernel --cov-report=term-missing
```
