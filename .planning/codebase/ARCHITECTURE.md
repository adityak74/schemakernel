# Architecture

**Analysis Date:** 2026-04-19

## Pattern Overview

**Overall:** Layered pipeline with LLM-driven adaptive schema planning

**Key Characteristics:**
- An LLM (via `instructor`-structured output) acts as the "planner" — it decides which form fields to add, update, hide, or finalize each turn
- All planner output is validated by a `ValidationEngine` before being applied to mutable session state
- Session state is persisted via an abstract `StorageBackend`, with `InMemoryStore` as the bundled implementation
- The entire public API is a single orchestrator class (`WorkflowStateMachine`) assembled via a factory function (`create_workflow`)
- Pydantic v2 models are used pervasively for data definitions, enforcing invariants at construction time

## Layers

**Models (data definitions):**
- Purpose: Frozen/validated Pydantic models representing all domain objects — fields, validators, planner actions, schema state, responses
- Location: `schemakernel/models.py`
- Contains: `FieldDefinition`, `FieldType`, `ValidatorRule`, `PlannerAction`, `PlannerResponse`, `SchemaState`, `WorkflowStage`, `ConditionalLogic`, `CompletionOutcome`, `PlannerTrace`
- Depends on: nothing (leaf layer)
- Used by: all other layers

**Policy (configuration):**
- Purpose: Operator-supplied configuration governing planner behavior — baseline fields, prohibited topics, completion criteria, LLM provider/model settings
- Location: `schemakernel/policy.py`
- Contains: `PolicyConfig`, `CompletionCriteria`, `EscalationCondition`, `ExceptionRule`
- Depends on: `models.py` (FieldDefinition)
- Used by: `planner.py`, `validation.py`, `workflow.py`

**Planner (LLM integration):**
- Purpose: Wraps Anthropic or OpenAI client via `instructor` to produce structured `PlannerResponse` objects from session context
- Location: `schemakernel/planner.py`
- Contains: `PlannerClient`
- Depends on: `policy.py`, `models.py`, `anthropic`/`openai` SDKs, `instructor`
- Used by: `workflow.py`

**Validation (safety gate):**
- Purpose: Double-validates all planner output (allowlists, policy checks, cross-references) and all user-submitted answers (type coercion + per-rule checks)
- Location: `schemakernel/validation.py`
- Contains: `ValidationEngine`, `ValidationResult`
- Depends on: `models.py`, `policy.py`, `exceptions.py`
- Used by: `workflow.py`

**Storage (session persistence):**
- Purpose: Abstract interface for persisting `SchemaState`, `PlannerTrace`, and `CompletionOutcome`
- Location: `schemakernel/store.py`
- Contains: `StorageBackend` (ABC), `InMemoryStore` (thread-safe default)
- Depends on: `models.py`, `exceptions.py`
- Used by: `workflow.py`

**Workflow (orchestrator):**
- Purpose: Stateful session manager — owns the session lifecycle, invokes the planner, gates on validation, applies actions to state, persists results
- Location: `schemakernel/workflow.py`
- Contains: `WorkflowStateMachine`, `create_workflow` factory
- Depends on: all other layers
- Used by: callers (library consumers)

**Exceptions:**
- Purpose: Layered exception hierarchy rooted at `SchemakernelError`
- Location: `schemakernel/exceptions.py`
- Contains: planner errors (`PlannerError`, `PlannerRetryExhausted`, `PlannerOutputRejected`), validation errors (`FieldValidationError`, `PolicyViolationError`), workflow errors (`TurnLimitExceeded`, `SessionNotFound`, `InvalidTransition`)
- Depends on: nothing
- Used by: all layers

## Data Flow

**Session initialization:**
1. Caller invokes `WorkflowStateMachine.start_session()`
2. A `SchemaState` is created; baseline fields from `PolicyConfig.baseline_questions` are copied in
3. Stage transitions to `COLLECTING`; state is saved to `StorageBackend`
4. A deep copy of the state is returned to the caller

**Planner turn:**
1. Caller invokes `WorkflowStateMachine.run_planner_turn(session_id)`
2. `WorkflowStateMachine` loads state from store; checks `turn_count` against `policy.max_turns`
3. System prompt and messages are built from current state + policy context
4. `PlannerClient.call()` sends prompt to the LLM (Anthropic/OpenAI via `instructor`), receiving a structured `PlannerResponse`
5. `ValidationEngine.validate_planner_response()` runs 8 checks (allowlists, policy, cross-references) against the response
6. If invalid: a `PlannerTrace` with `validated=False` is saved and `PlannerOutputRejected` is raised
7. If valid: actions are applied to state via `_apply_actions()`, turn count increments, audit log is appended
8. On `COMPLETE` or `ESCALATE` status: a `CompletionOutcome` is persisted
9. State is saved; a deep copy is returned

**Answer submission:**
1. Caller invokes `WorkflowStateMachine.submit_answer(session_id, field_key, value)`
2. Field existence is checked in current state
3. `ValidationEngine.validate_answer()` coerces the value to the field's type, then runs all `ValidatorRule` checks
4. If valid: answer is stored in `state.answers`, audit log is appended, state is saved

**Conditional field visibility:**
1. `WorkflowStateMachine.get_next_fields()` iterates `state.field_order`
2. For each field: checks `ask_if_missing`, already-answered, and evaluates `visible_if` via `_evaluate_condition()`
3. Returns unanswered, visible fields sorted by `priority`

**State Management:**
- All mutable session data lives in `SchemaState` (fields dict, field_order list, answers dict, stage enum, turn_count, audit_log)
- `StorageBackend` always stores/returns deep copies to prevent aliasing
- `InMemoryStore` uses a `threading.Lock` for thread safety

## Key Abstractions

**FieldDefinition:**
- Purpose: A single form field specification — type, label, validators, visibility conditions, priority
- Examples: `schemakernel/models.py` lines 120-154
- Pattern: Pydantic `BaseModel` with cross-field `model_validator`s enforcing invariants (e.g., SELECT requires options, ui_props forbids executable patterns)

**PlannerResponse:**
- Purpose: Structured LLM output — a list of `PlannerAction`s, accompanying `FieldDefinition`s, rationale, and completion status
- Examples: `schemakernel/models.py` lines 186-218
- Pattern: Frozen Pydantic model with validators ensuring ADD/UPDATE actions have matching field defs and COMPLETE/ESCALATE actions match completion_status

**StorageBackend (ABC):**
- Purpose: Pluggable persistence interface; callers swap implementations without changing workflow logic
- Examples: `schemakernel/store.py` lines 10-30
- Pattern: Abstract base class with 7 abstract methods; `InMemoryStore` is the concrete default

**PolicyConfig:**
- Purpose: Operator-supplied configuration bundle passed at construction time; controls planner behavior, LLM selection, limits
- Examples: `schemakernel/policy.py` lines 33-57
- Pattern: Pydantic model with frozen sub-models for immutable policy sub-sections

**ConditionalLogic / ALWAYS_HIDDEN sentinel:**
- Purpose: Declarative conditions evaluated against `state.answers` to control field visibility
- Examples: `schemakernel/models.py` lines 102-115, 222-231
- Pattern: `ALWAYS_HIDDEN` is a module-level sentinel `ConditionalLogic` that always evaluates False; used by the HIDE action

## Entry Points

**`create_workflow` factory:**
- Location: `schemakernel/workflow.py` line 366
- Triggers: Called by library consumers to instantiate the full engine
- Responsibilities: Creates `InMemoryStore`, `PlannerClient`, `ValidationEngine`, wires them into `WorkflowStateMachine`

**`WorkflowStateMachine.start_session`:**
- Location: `schemakernel/workflow.py` line 48
- Triggers: First call to begin a new data collection session
- Responsibilities: Creates `SchemaState`, loads baseline fields, saves to store

**`WorkflowStateMachine.run_planner_turn`:**
- Location: `schemakernel/workflow.py` line 95
- Triggers: Called each time the consumer wants the LLM to evolve the schema
- Responsibilities: Builds prompt, calls LLM, validates output, applies actions, persists state and traces

**Public package surface:**
- Location: `schemakernel/__init__.py`
- Triggers: `import schemakernel`
- Responsibilities: Re-exports all public symbols from all modules under a single namespace

## Error Handling

**Strategy:** Layered exception hierarchy under `SchemakernelError`; errors propagate up to the caller unless explicitly caught

**Patterns:**
- `ValidationEngine` methods return `ValidationResult(valid=False, errors=[...])` by default; pass `raise_on_failure=True` to raise instead
- `PlannerOutputRejected` is raised by `run_planner_turn` when the planner response fails validation
- `TurnLimitExceeded` is raised when `turn_count >= max_turns` before calling the LLM
- `SessionNotFound` is raised by `StorageBackend` when a session_id is unknown
- `PlannerRetryExhausted` wraps `instructor`'s retry exception class by name (to avoid version coupling)
- Each layer defines its own exception subclass; callers can catch at any granularity

## Cross-Cutting Concerns

**Logging:** None — audit trail is stored in `SchemaState.audit_log` (list of dicts) and `PlannerTrace` records persisted via `StorageBackend`

**Validation:** Two distinct passes — (1) `validate_planner_response` for LLM output safety, (2) `validate_answer` for user input correctness; both live in `ValidationEngine`

**Authentication:** Delegated entirely to the underlying SDK clients (`anthropic.Anthropic()`, `openai.OpenAI()`), which read API keys from environment variables

---

*Architecture analysis: 2026-04-19*
