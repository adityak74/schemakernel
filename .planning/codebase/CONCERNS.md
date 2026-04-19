# Concerns

**Analysis Date:** 2026-04-19

## Technical Debt

### No persistent storage implementation
**Severity:** Medium
**Location:** `schemakernel/store.py`
`InMemoryStore` is the only concrete `StorageBackend`. All session data is lost on process restart. Any production deployment requires a custom implementation (Redis, PostgreSQL, etc.) — there are no bundled persistent backends and no migration utilities.

### No async support
**Severity:** Medium
**Location:** `schemakernel/workflow.py`, `schemakernel/planner.py`
The entire API is synchronous. `PlannerClient.call()` makes blocking HTTP requests to the LLM provider. Serving concurrent sessions in an async web framework (FastAPI, Starlette) requires thread pool workarounds. `pyproject.toml` includes `pytest-asyncio` but there are no async code paths.

### `instructor` version coupling via string inspection
**Severity:** Low
**Location:** `schemakernel/planner.py`
`PlannerRetryExhausted` is raised by catching the `instructor` retry exception by class name (`type(e).__name__`) to avoid hard coupling to `instructor` internals. This is fragile — a rename or restructure in `instructor` will silently swallow retries.

### Prompt construction is opaque
**Severity:** Low
**Location:** `schemakernel/workflow.py` (`_build_prompt`)
The system prompt and message list are built inline with string formatting. There is no template system, no prompt versioning, and no mechanism to A/B test prompt changes. Iterating on prompt quality requires editing library code.

## Known Gaps

### No rate limiting or backoff
**Severity:** Medium
**Location:** `schemakernel/planner.py`
LLM API calls have no client-side rate limiting or exponential backoff beyond `instructor`'s built-in retry count. Burst usage will surface as unhandled `anthropic.RateLimitError` / `openai.RateLimitError`.

### No session TTL / expiry
**Severity:** Low
**Location:** `schemakernel/store.py`
`InMemoryStore` grows unbounded — no TTL, no eviction, no size cap. Long-running processes with many sessions will exhaust memory.

### `audit_log` is untyped
**Severity:** Low
**Location:** `schemakernel/models.py` (`SchemaState.audit_log`)
`audit_log` is `list[dict]` — no schema enforcement on entries. Log consumers must guess the structure. Typed audit entries would make the log more useful.

## Security

### `ui_props` scalar-only enforcement is pattern-based
**Severity:** Low
**Location:** `schemakernel/models.py` (`FieldDefinition` validator)
`ui_props` values are restricted to `str | int | float | bool` scalars via a Pydantic validator that also rejects strings matching executable patterns (`__`, `eval`, `exec`, `import`, `lambda`). The allowlist approach is sound but relies on string matching — a determined attacker with control over `PolicyConfig.baseline_questions` could craft edge cases. The real protection is that `PolicyConfig` is operator-supplied, not user-supplied.

### API keys in environment — no validation at startup
**Severity:** Low
**Location:** `schemakernel/planner.py`
API key existence is not validated at `create_workflow()` time — missing keys surface only at the first `run_planner_turn()` call as an SDK exception.

## Fragile Areas

### `_apply_actions` ordering dependency
**Location:** `schemakernel/workflow.py`
Action application order matters — `REORDER` after `ADD` on the same turn works, but some action orderings within a single `PlannerResponse` could produce unexpected state. The planner is not explicitly constrained on action ordering.

### Thread safety limited to `InMemoryStore`
**Location:** `schemakernel/store.py`
`InMemoryStore` is thread-safe via `threading.Lock`. `WorkflowStateMachine` itself is stateless per call (session data lives in the store), which is correct. However, if a custom `StorageBackend` drops the lock, concurrent `run_planner_turn` calls for the same session_id will race.

---

*Concerns analysis: 2026-04-19*
