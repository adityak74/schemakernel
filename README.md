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
| `schemakernel` | Core engine (this package) |
| `schemakernel.streamlit` | Streamlit adapter (Phase 2) |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=schemakernel
```
