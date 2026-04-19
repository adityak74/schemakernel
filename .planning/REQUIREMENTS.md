# Requirements: SchemaKernel

## Functional Requirements

### 1. Canonical Schema Model
- Support field attributes: `key`, `type`, `label`, `description`, `required`, `validators`, `ui_props`, `visible_if`.
- Support incremental schema patches.
- Strict validation of field keys and scalar-only `ui_props`.

### 2. Planner Contract (LLM)
- Defined actions: `add`, `update`, `remove`, `require`, `hide`, `show`, `reorder`, `complete`, `escalate`.
- Return rationale and completion status.
- Integration with `instructor` for structured Pydantic output.

### 3. Validation Engine
- Enforce types and rules (min, max, length, regex, enum).
- Allowlist-based gate for all planner actions and field types.
- Deterministic execution in the host runtime.

### 4. Workflow State Machine
- Manage session lifecycle: `INITIALIZED` -> `COLLECTING` -> `COMPLETE`/`ESCALATED`.
- Persist state (fields, answers, audit logs) via abstract storage.
- Support turn-based evolution of the schema.

### 5. Adapters
- **Streamlit:** Use `st.form` and `st.session_state` for adaptive form rendering.
- **JavaScript (Future):** JSON-schema compatible output for systems like SurveyJS.

## Non-Functional Requirements
- **Safety:** No execution of arbitrary code or raw HTML from LLM.
- **Auditability:** Log all planner rationale and state changes.
- **Performance:** Efficient schema patching to minimize token overhead.
- **Reliability:** Handle LLM retries and validation failures gracefully.

## Constraints
- Python 3.11+
- Pydantic v2
- Instructor-compatible LLM provider (Anthropic, OpenAI)
