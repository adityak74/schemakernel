# Roadmap: SchemaKernel

## Phase 1: Core Engine Implementation (Completed)
**Goal:** Reach 100% coverage, ensure all edge cases in validation and state transitions are tested, and verify the Instructor-based planner integration.

- [x] Canonical Schema Models (`models.py`)
- [x] Exception Hierarchy (`exceptions.py`)
- [x] Storage Abstraction & InMemoryStore (`store.py`)
- [x] Validation Engine (`validation.py`)
- [x] Policy Configuration (`policy.py`)
- [x] Instructor-based Planner Client (`planner.py`)
- [x] Workflow State Machine & Factory (`workflow.py`)
- [x] Comprehensive Unit & Integration Tests

## Phase 2: Streamlit Adapter (Completed)
**Goal:** Deliver first-party Streamlit support using `st.form` and `st.session_state`.

- [x] Streamlit Form Adapter
- [x] Session State Persistence Layer
- [x] Reference Implementation / Examples (Intake, Screening)
- [x] Developer Documentation for Streamlit Integration

## Phase 3: JavaScript SDK (Planned)
**Goal:** Deliver a TypeScript SDK with renderer adapters.

**Plans:** 5 plans
- [ ] 03-01-PLAN.md — JS Infrastructure & Models
- [ ] 03-02-PLAN.md — SDK Core Logic (Store, Policy, Validation)
- [ ] 03-03-PLAN.md — Workflow & AI (Workflow, Planner)
- [x] 03-04-PLAN.md — Adapters (SurveyJS, Express)
- [ ] 03-05-PLAN.md — Parity Testing & Build

## Phase 4: Production Capabilities (Planned)
**Goal:** Persistence backends, observability, and enterprise features.

- [ ] Cloud Storage Backends (PostgreSQL, DynamoDB)
- [ ] Prompt Versioning & A/B Testing
- [ ] Telemetry & Audit Dashboards
- [ ] Compliance Redaction Tooling
- [ ] Enterprise Deployment Templates
