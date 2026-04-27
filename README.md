# SchemaKernel

Adaptive form engine powered by LLM-driven structured field planning.

SchemaKernel lets an LLM decide which fields to ask, how to validate responses, and when to ask follow-up questions — while keeping rendering fully deterministic. It produces structured field definitions, validation rules, branching logic, and completion signals consumed by UI renderers. It does **not** generate HTML.

## Key Features

- **LLM-Driven Planning:** Uses [Instructor](https://github.com/instructor-ai/instructor) for safe, structured schema patches.
- **Deterministic Runtimes:** Shared logic across **Python** and **TypeScript** via test-vector parity.
- **First-Class Adapters:** Built-in support for **Streamlit** (Python) and **SurveyJS** (JavaScript).
- **Production Ready:** SQL/DynamoDB storage, OpenTelemetry tracing, and PII redaction.
- **Safety First:** Strict allowlists for all LLM actions and field/validator types.

## Installation

### Python
```bash
pip install schemakernel
```

### JavaScript / TypeScript
```bash
cd js-sdk
npm install @schemakernel/sdk
```

## Quick Start (Python)

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

## Streamlit Support

SchemaKernel includes first-class support for Streamlit.

```python
import streamlit as st
from schemakernel import create_workflow, StreamlitSessionStore, StreamlitFormAdapter

store = StreamlitSessionStore()
adapter = StreamlitFormAdapter()

wf = create_workflow(store=store)
state = wf.get_state(st.session_id)

answers = adapter.render_step(state.fields, state.answers)
if answers:
    wf.submit_answers(state.session_id, answers)
    wf.run_planner_turn(state.session_id)
    st.rerun()
```

### Run the Example App

```bash
streamlit run examples/streamlit_app.py
```

## JavaScript SDK & SurveyJS

The `@schemakernel/sdk` provides full parity with the Python engine.

```typescript
import { WorkflowStateMachine, SurveyJSAdapter } from "@schemakernel/sdk";

const wf = new WorkflowStateMachine(policy, store, planner);
const state = await wf.startSession();

const adapter = new SurveyJSAdapter();
const surveyJson = adapter.renderStep(state); // Ready for SurveyJS renderer
```

## Production Capabilities

- **Storage:** `SQLStorageBackend` (PostgreSQL) and `DynamoDBStorageBackend`.
- **Observability:** Structured JSON logging (`structlog`) and OpenTelemetry tracing.
- **Compliance:** `RedactingStorageWrapper` using Microsoft Presidio to scrub PII before persistence.
- **Versioning:** Built-in policy versioning and deterministic A/B testing (Experiment Routing).

## Architecture

SchemaKernel is a schema execution kernel:

1. **Policy** — defines baseline questions, glossary, rules, and completion criteria.
2. **Planner** — calls the LLM and returns a typed `PlannerResponse`.
3. **ValidationEngine** — enforces allowlists before any state mutation.
4. **WorkflowStateMachine** — orchestrates the loop: start → collect → plan → apply → repeat.

## Development

```bash
# Python
pip install -e ".[dev]"
pytest

# JavaScript
cd js-sdk
npm install
npm test
npm run build
```

## Deployment

For production deployment using Docker and Kubernetes, see [DEPLOYMENT.md](DEPLOYMENT.md).
