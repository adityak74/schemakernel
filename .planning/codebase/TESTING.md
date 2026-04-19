# Testing

**Analysis Date:** 2026-04-19

## Framework & Configuration

**Framework:** pytest 8.3+
**Config:** `pyproject.toml` `[tool.pytest.ini_options]`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--tb=short -q"
```

**Dev dependencies:** `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-mock`

**Run tests:**
```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=schemakernel --cov-report=term-missing
```

## Test Structure

```
tests/
├── conftest.py         # shared fixtures + helper factories
├── test_models.py      # Pydantic model invariants, cross-field validators
├── test_validation.py  # ValidationEngine unit tests
├── test_planner.py     # PlannerClient (mocked instructor/LLM)
├── test_store.py       # InMemoryStore (CRUD, thread safety)
└── test_workflow.py    # WorkflowStateMachine (integration-level)
```

## Fixtures (conftest.py)

| Fixture | Type | Purpose |
|---------|------|---------|
| `minimal_field` | `FieldDefinition` | Simplest valid text field |
| `select_field` | `FieldDefinition` | SELECT field with options |
| `validated_field` | `FieldDefinition` | INTEGER field with MIN/MAX validators |
| `minimal_policy` | `PolicyConfig` | Policy with 1 baseline field, max_turns=5 |
| `in_memory_store` | `InMemoryStore` | Fresh in-memory store |
| `mock_planner` | `MagicMock` | PlannerClient mock returning add-field response |
| `workflow` | `WorkflowStateMachine` | Fully wired workflow with mock planner |

## Helper Factories (conftest.py)

```python
make_add_response(field: FieldDefinition) -> PlannerResponse
make_complete_response() -> PlannerResponse
```

Used to construct valid `PlannerResponse` objects for planner mocking.

## Mocking Strategy

**LLM (PlannerClient):** Replaced with `MagicMock`; `planner.call.return_value` set to a pre-built `PlannerResponse`. No real API calls in tests.

**Storage:** `InMemoryStore` used directly — no mocking needed (it's in-process and deterministic).

**instructor / Anthropic SDK:** Not mocked at the SDK level — `PlannerClient` itself is replaced at the workflow boundary.

## Patterns

**Model invariant tests** (`test_models.py`):
- Construct models with invalid combinations → expect `ValidationError`
- Example: `FieldType.SELECT` without `options`, `ui_props` with executable content, key pattern violations

**Validation unit tests** (`test_validation.py`):
- Call `ValidationEngine.validate_answer()` / `validate_planner_response()` directly
- Pass known-valid and known-invalid inputs, assert `ValidationResult.valid` and `errors`

**Workflow integration tests** (`test_workflow.py`):
- Use the `workflow` fixture (wired with `mock_planner`)
- Call `start_session()` → `run_planner_turn()` → `submit_answer()` in sequence
- Assert state transitions (`stage`, `turn_count`, `answers`, `audit_log`)

## Coverage

**Command:**
```bash
pytest --cov=schemakernel --cov-report=term-missing
```

**Target:** All public methods in all modules covered by at least one test.

---

*Testing analysis: 2026-04-19*
