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

## Phase 3: JavaScript SDK (Completed)
**Goal:** Deliver a TypeScript SDK with renderer adapters.

- [x] TypeScript Canonical Schema Definitions
- [x] JavaScript Adapter for SurveyJS
- [x] Server-side Orchestration Middleware (Node.js/Express)
- [x] Multi-runtime Parity Testing

## Phase 4: Production Capabilities (Planned)
**Goal:** Persistence backends, observability, and enterprise features.

**Plans:** 5 plans
- [ ] 04-01-PLAN.md — SQL & DynamoDB Storage Backends
- [ ] 04-02-PLAN.md — Observability & Telemetry (OpenTelemetry integration)
- [ ] 04-03-PLAN.md — Policy Versioning & A/B Testing
- [ ] 04-04-PLAN.md — Compliance & Redaction (Presidio integration)
- [ ] 04-05-PLAN.md — Enterprise Deployment (Docker & Helm)

- [ ] Cloud Storage Backends (PostgreSQL, DynamoDB)
- [ ] Prompt Versioning & A/B Testing
- [ ] Telemetry & Audit Dashboards
- [ ] Compliance Redaction Tooling
- [ ] Enterprise Deployment Templates
