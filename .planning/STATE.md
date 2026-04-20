# Project State: SchemaKernel

## Current Focus
- Phase 2: Streamlit Adapter (Implementing).
- Developing Streamlit form renderer.

## Recent Decisions
- LLM integration is constrained via `instructor` to enforce structured Pydantic outputs.
- `ui_props` in `FieldDefinition` will only support scalar values (str, int, float, bool) for safety.
- `StorageBackend` uses deep copies during persistence and retrieval to prevent state corruption.
- Core engine verified with 99% project-wide test coverage.
- States are stored in `st.session_state` with a configurable prefix (default 'sk_') to avoid collisions.
- Streamlit is imported lazily to avoid a hard dependency for users not using the Streamlit adapter.

## Open Questions / Blockers
- Should scoring and summarization be first-class outputs in Phase 1 or deferred to Phase 4? (Deferred per current roadmap)
- Confirmation of specific JavaScript renderer for initial SDK development (SurveyJS is the lead candidate).

## Progress
- **Phase 2 Plan 1:** Completed (Streamlit Session Store)
- **Current Plan:** Phase 2 Plan 2 (Streamlit Form Adapter)

## Current Milestone: Streamlit Integration
- **Status:** Implementing
- **Next Task:** Execute Wave 1 of Phase 2 (Streamlit Form Adapter).
