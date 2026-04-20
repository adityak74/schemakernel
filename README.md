# SchemaKernel

Adaptive form engine powered by LLM-driven structured field planning.

SchemaKernel lets an LLM decide which fields to ask, how to validate responses, and when to ask follow-up questions — while keeping rendering fully deterministic. It produces structured field definitions, validation rules, branching logic, and completion signals consumed by UI renderers. It does **not** generate HTML.

## Quick Start

```python
from schemakernel import create_workflow, PolicyConfig, FieldDefinition, FieldType

policy = PolicyConfig(
    baseline_questions=[
        FieldDefinition(key="name", type=FieldType.TEXT, label="Your full name"),
        FieldDefinition(key="age", type=FieldType.INTEGER, label="Your age"),
    ],
    completion_criteria={"minimum_answered_count": 2},
)

wf = create_workflow(policy)
state = wf.start_session()

# Submit answers
wf.submit_answer(state.session_id, "name", "Alice")
wf.submit_answer(state.session_id, "age", 30)

# Ask the planner what to do next
state = wf.run_planner_turn(state.session_id)
print(state.stage)  # collecting | complete | escalate
```

## Installation

```bash
pip install schemakernel
```

Requires Python 3.11+. Set `ANTHROPIC_API_KEY` (default provider) or `OPENAI_API_KEY`.

## Streamlit Support

SchemaKernel includes first-class support for Streamlit. You can use the `StreamlitSessionStore` to automatically persist workflow state in `st.session_state` and the `StreamlitFormAdapter` to render fields as native Streamlit widgets.

```python
import streamlit as st
from schemakernel import create_workflow, StreamlitSessionStore, StreamlitFormAdapter

# 1. Setup persistence and rendering
store = StreamlitSessionStore()
adapter = StreamlitFormAdapter()

# 2. Create or load workflow
wf = create_workflow(planner=my_planner, store=store, session_id="user-123")
state = wf.get_state()

# 3. Render and capture answers
answers = adapter.render_step(state.active_fields, state.captured_data)
if answers:
    wf.submit_answers(answers)
    st.rerun()
```

### Run the Example App

Check out the full reference implementation:

```bash
pip install streamlit
streamlit run examples/streamlit_app.py
```

## Architecture

SchemaKernel is a schema execution kernel:

1. **Policy** — defines baseline questions, glossary, exception rules, prohibited topics, completion criteria.
2. **Planner** — calls the LLM via [Instructor](https://github.com/instructor-ai/instructor) and returns a typed `PlannerResponse`.
3. **ValidationEngine** — enforces allowlists (action types, field types, validator types) before any state mutation.
4. **WorkflowStateMachine** — orchestrates the loop: start → collect answers → run planner → apply schema patch → repeat.
5. **StorageBackend** — persists session state, planner traces, and completion outcomes.

## Packages

| Package | Description |
|---|---|
| `schemakernel` | Core engine |
| `schemakernel.adapters.streamlit` | Streamlit adapter (Session state store and form renderer) |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=schemakernel
```
