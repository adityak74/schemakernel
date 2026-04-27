# Phase 2: Streamlit Adapter - Research

**Researched:** 2024-05-23
**Domain:** Streamlit Integration & Dynamic Forms
**Confidence:** HIGH

## Summary

This phase focuses on extending the SchemaKernel core with a first-party Streamlit adapter. The goal is to allow Python developers to render adaptive forms using `st.form` and persist workflow state in `st.session_state`. 

Streamlit's execution model (rerunning on every interaction) makes `st.session_state` the primary mechanism for state persistence. For adaptive forms where the schema changes based on LLM planning, the batching capability of `st.form` is essential to prevent multiple expensive planner calls or UI flickers while the user fills out a step.

**Primary recommendation:** Use a dedicated `StreamlitSessionStore` that implements the `StorageBackend` interface using `st.session_state`, and provide a `StreamlitFormAdapter` that maps canonical `FieldType` enums to native Streamlit widgets.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.46.1 | UI Framework | Primary target for Python adaptive forms. [VERIFIED: pip show] |
| pydantic | 2.10.6 | Data Validation | Core engine dependency for schema models. [VERIFIED: project context] |
| schemakernel | 0.1.0 | Core Engine | The core logic to be adapted. [VERIFIED: project context] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| streamlit.testing.v1 | — | Automated Testing | Use `AppTest` for verifying the adapter UI. [CITED: streamlit docs] |

**Installation:**
```bash
pip install streamlit schemakernel
```

## Architecture Patterns

### Recommended Project Structure
```
schemakernel/
├── adapters/
│   ├── __init__.py
│   └── streamlit.py   # StreamlitFormAdapter, StreamlitSessionStore
└── ...
examples/
├── streamlit_intake.py
└── streamlit_screening.py
```

### Pattern 1: Session State Storage
Implementing `StorageBackend` using `st.session_state` allows the `WorkflowStateMachine` to remain agnostic of the hosting environment while benefiting from Streamlit's per-user persistence.

**Example:**
```python
# [ASSUMED] - Proposed implementation pattern
class StreamlitSessionStore(StorageBackend):
    def __init__(self, key_prefix="sk_"):
        self.prefix = key_prefix
    
    def save_state(self, state: SchemaState):
        st.session_state[f"{self.prefix}state_{state.session_id}"] = state
    
    def load_state(self, session_id: str) -> SchemaState:
        key = f"{self.prefix}state_{session_id}"
        if key not in st.session_state:
            raise SessionNotFound(session_id)
        return st.session_state[key]
```

### Pattern 2: Form Batching Loop
Using `st.form` to collect a "step" of answers before running the planner. This aligns with the "staged submission" requirement.

**Workflow:**
1. Retrieve "next fields" from `WorkflowStateMachine`.
2. Render fields inside `st.form`.
3. On `st.form_submit_button`:
   - Submit all answers to `WorkflowStateMachine`.
   - Call `run_planner_turn()`.
   - `st.rerun()` to show new fields or completion state.

### Anti-Patterns to Avoid
- **Hardcoding widgets:** Don't write `st.text_input` manually for each field; use a mapping function from `FieldType`.
- **Global Store:** Avoid using `InMemoryStore` for Streamlit if you want persistence across page refreshes (though `st.session_state` also clears on refresh, it is the idiomatic way for Streamlit).
- **Infinite Reruns:** Ensure `st.rerun()` is only called after a state-changing event (like form submission) to avoid loops.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State management | Custom dict in session state | `WorkflowStateMachine` | Handles stage transitions, turn counts, and audit logs. |
| Schema Merging | Custom dict.update() logic | `_apply_actions` in core | Handles complex actions like REORDER, HIDE, and REQUIRE safely. |
| Validation | Manual if/else checks | `ValidationEngine` | Standardizes error messages and supports complex rules (regex, date bounds). |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| streamlit | UI Rendering | ✓ | 1.46.1 | — |
| python | Runtime | ✓ | 3.12.1 | — |

## Common Pitfalls

### Pitfall 1: Dynamic Field Keys
**What goes wrong:** Streamlit widgets reset or throw "Duplicate Key" errors if keys are not stable or are reused across different stages.
**How to avoid:** Use the canonical `field.key` as the Streamlit widget `key`. Ensure `field.key` is unique within the schema (enforced by `FieldDefinition` validation).

### Pitfall 2: Form Interaction Limitations
**What goes wrong:** `visible_if` (conditional logic) does NOT update in real-time *inside* a `st.form`.
**How to avoid:** Document that `visible_if` in a Streamlit context will only update after the form is submitted (batch mode). For real-time interactivity, developers should use `st.container` with individual buttons, but the primary adapter will focus on the `st.form` batching pattern as requested.

### Pitfall 3: LLM Latency
**What goes wrong:** The UI hangs while `run_planner_turn()` calls the LLM.
**How to avoid:** Wrap the planner turn in `st.spinner("Thinking...")`.

## Code Examples

### Widget Mapping
```python
# [ASSUMED] - Proposed mapping
WIDGET_MAP = {
    FieldType.TEXT: st.text_input,
    FieldType.NUMBER: st.number_input,
    FieldType.BOOLEAN: st.checkbox,
    FieldType.SELECT: st.selectbox,
    FieldType.DATE: st.date_input,
    FieldType.TEXTAREA: st.text_area,
}

def render_field(field: FieldDefinition, current_value: Any):
    widget_func = WIDGET_MAP.get(field.type, st.text_input)
    kwargs = {"label": field.label, "help": field.description, "key": field.key}
    if field.type == FieldType.SELECT:
        kwargs["options"] = field.options
    # ... handle value and default ...
    return widget_func(**kwargs)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + streamlit.testing.v1 |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_streamlit_adapter.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ST-01 | Render fields to widgets | Integration | `pytest tests/test_streamlit_adapter.py` | ❌ Wave 0 |
| ST-02 | Persist in session_state | Integration | `pytest tests/test_streamlit_adapter.py` | ❌ Wave 0 |
| ST-03 | Handle form submission | E2E (AppTest) | `pytest tests/test_streamlit_adapter.py` | ❌ Wave 0 |

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `schemakernel.validation.ValidationEngine` |
| V12 File and Resources | no | — |

### Known Threat Patterns for Streamlit

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| State Injection | Tampering | Validate session IDs and use Pydantic for state deserialization. |
| XSS in Labels | Tampering | Streamlit's `st.text` and `st.write` sanitize output; SchemaKernel's `FieldDefinition` forbids executable patterns in `ui_props`. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `st.session_state` is sufficient for persistence in this phase | Summary | Users might expect database persistence (Phase 4). |
| A2 | `st.datetime_input` combination is needed | Standard Stack | Developers might want a single 3rd-party datetime widget instead. |
| A3 | `AppTest` is the preferred testing method | Validation | Some environments might have trouble running headless Streamlit. |

## Sources

### Primary (HIGH confidence)
- `schemakernel/models.py`, `workflow.py` - Core logic verified.
- `pip show streamlit` - Version 1.46.1 confirmed.
- Streamlit Official Documentation - `st.form`, `st.session_state`, and `AppTest` features confirmed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Current versions verified.
- Architecture: HIGH - Aligns with Streamlit idioms.
- Pitfalls: MEDIUM - Based on common Streamlit community issues.

**Research date:** 2024-05-23
**Valid until:** 2024-06-22
