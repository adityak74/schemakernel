# External Integrations

**Analysis Date:** 2026-04-19

## APIs & External Services

**LLM Providers (both supported; one active per session):**

- Anthropic Claude API - Powers the `PlannerClient` when `PolicyConfig.provider = "anthropic"`
  - SDK/Client: `anthropic>=0.40,<1` + `instructor>=1.14,<2`
  - Auth: `ANTHROPIC_API_KEY` environment variable (read by `anthropic.Anthropic()` at client construction in `schemakernel/planner.py`)
  - Default model: `claude-sonnet-4-6`
  - Usage: `instructor.from_anthropic(raw).chat.completions.create_with_completion(...)` returning typed `PlannerResponse`

- OpenAI API - Powers the `PlannerClient` when `PolicyConfig.provider = "openai"`
  - SDK/Client: `openai>=1.40` + `instructor>=1.14,<2`
  - Auth: `OPENAI_API_KEY` environment variable (read by `openai.OpenAI()` at client construction in `schemakernel/planner.py`)
  - Usage: `instructor.from_openai(raw).chat.completions.create_with_completion(...)` returning typed `PlannerResponse`

## Data Storage

**Databases:**
- None - No database is used. All state is held in process memory via `InMemoryStore` (`schemakernel/store.py`).
- A `StorageBackend` abstract base class exists at `schemakernel/store.py` to allow external implementations (e.g., Redis, PostgreSQL). Three abstract method pairs: `save_state`/`load_state`, `save_trace`/`list_traces`, `save_outcome`/`load_outcome`.

**File Storage:**
- Local filesystem only - No cloud file storage integration.

**Caching:**
- None - No caching layer. Each LLM call is made fresh.

## Authentication & Identity

**Auth Provider:**
- None - SchemaKernel is a library with no user authentication. Identity is not modeled.
- Session identity is a UUID string generated via `uuid.uuid4()` in `schemakernel/workflow.py`.

## Monitoring & Observability

**Error Tracking:**
- None - No Sentry, Datadog, or similar integration.

**Logs:**
- None - No logging framework calls found in the codebase. Errors propagate as typed exceptions from `schemakernel/exceptions.py`.

**Tracing:**
- Internal only - `PlannerTrace` (a Pydantic model at `schemakernel/models.py`) records each LLM turn's raw response, validation status, and rejection reason. Stored in `InMemoryStore._traces` keyed by `session_id`.

## CI/CD & Deployment

**Hosting:**
- Not applicable - Pure Python library, distributed as a package.

**CI Pipeline:**
- Not present - No `.github/`, `.circleci/`, or similar CI config files detected.

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` - Required when using Anthropic provider (default)
- `OPENAI_API_KEY` - Required when using OpenAI provider

**Secrets location:**
- Environment variables only; no `.env` file present or committed.

## Webhooks & Callbacks

**Incoming:**
- None - SchemaKernel is a library; it exposes no HTTP endpoints.

**Outgoing:**
- None - No webhook dispatch logic present.

## Structured Output Bridge (instructor)

`instructor` is the critical integration layer between the LLM APIs and the application's type system.

- It wraps both `anthropic.Anthropic()` and `openai.OpenAI()` clients.
- The `response_model=PlannerResponse` parameter instructs instructor to validate LLM JSON output against the Pydantic `PlannerResponse` model.
- Retry logic on malformed responses is delegated to instructor via `max_retries` parameter.
- Instructor's `InstructorRetryException` is caught by name (not by import) in `schemakernel/planner.py` to avoid version coupling:
  ```python
  if type(exc).__name__ == "InstructorRetryException":
      raise PlannerRetryExhausted(...)
  ```

---

*Integration audit: 2026-04-19*
