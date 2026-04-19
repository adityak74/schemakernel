# Project State: SchemaKernel

## Current Focus
- Completing Phase 1 (Core Engine Implementation).
- Finalizing test coverage for validation and workflow state machine.

## Recent Decisions
- LLM integration is constrained via `instructor` to enforce structured Pydantic outputs.
- `ui_props` in `FieldDefinition` will only support scalar values (str, int, float, bool) for safety.
- `StorageBackend` uses deep copies during persistence and retrieval to prevent state corruption.

## Open Questions / Blockers
- Should scoring and summarization be first-class outputs in Phase 1 or deferred to Phase 4? (Deferred per current roadmap)
- Confirmation of specific JavaScript renderer for initial SDK development (SurveyJS is the lead candidate).

## Current Milestone: Core Engine Prototype
- **Status:** Implementing
- **Next Task:** Comprehensive unit and integration testing.
