# Roadmap: SchemaKernel

## Phase 1: Core Engine Implementation (Implementing)
**Goal:** Deliver canonical schema models, planner contracts, validation engine, policy model, and in-memory storage.

- [x] Canonical Schema Models (`models.py`)
- [x] Exception Hierarchy (`exceptions.py`)
- [x] Storage Abstraction & InMemoryStore (`store.py`)
- [x] Validation Engine (`validation.py`)
- [x] Policy Configuration (`policy.py`)
- [x] Instructor-based Planner Client (`planner.py`)
- [x] Workflow State Machine & Factory (`workflow.py`)
- [ ] Comprehensive Unit & Integration Tests (In Progress)

## Phase 2: Streamlit Adapter (Upcoming)
**Goal:** Deliver first-party Streamlit support using `st.form` and `st.session_state`.

- [ ] Streamlit Form Adapter
- [ ] Session State Persistence Layer
- [ ] Reference Implementation / Examples (Intake, Screening)
- [ ] Developer Documentation for Streamlit Integration

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
