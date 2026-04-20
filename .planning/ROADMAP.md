# Roadmap: SchemaKernel

## Phase 1: Core Engine Implementation (Completed)
**Goal:** Reach 100% coverage, ensure all edge cases in validation and state transitions are tested, and verify the Instructor-based planner integration.

**Plans:** 3 plans

- [x] Canonical Schema Models (`models.py`)
- [x] Exception Hierarchy (`exceptions.py`)
- [x] Storage Abstraction & InMemoryStore (`store.py`)
- [x] Validation Engine (`validation.py`)
- [x] Policy Configuration (`policy.py`)
- [x] Instructor-based Planner Client (`planner.py`)
- [x] Workflow State Machine & Factory (`workflow.py`)
- [x] Comprehensive Unit & Integration Tests
    - [x] 01-01-PLAN.md — Validation Engine Coverage (REQ-03)
    - [x] 01-02-PLAN.md — Workflow & State Machine Coverage (REQ-04)
    - [x] 01-03-PLAN.md — Planner & Integration Verification (REQ-02)

## Phase 2: Streamlit Adapter (Upcoming)
**Goal:** Deliver first-party Streamlit support using `st.form` and `st.session_state`.

**Plans:** 3 plans

- [ ] 02-01-PLAN.md — Streamlit Session Store (Persistence Layer)
- [ ] 02-02-PLAN.md — Streamlit Form Adapter (Renderer)
- [ ] 02-03-PLAN.md — Integration Example & Documentation

## Phase 3: JavaScript SDK (Planned)
**Goal:** Deliver a TypeScript SDK with renderer adapters.

- [ ] TypeScript Canonical Schema Definitions
- [ ] JavaScript Adapter for SurveyJS
- [ ] Server-side Orchestration Middleware (Node.js/Express)
- [ ] Multi-runtime Parity Testing

## Phase 4: Production Capabilities (Planned)
**Goal:** Persistence backends, observability, and enterprise features.

- [ ] Cloud Storage Backends (PostgreSQL, DynamoDB)
- [ ] Prompt Versioning & A/B Testing
- [ ] Telemetry & Audit Dashboards
- [ ] Compliance Redaction Tooling
- [ ] Enterprise Deployment Templates
