# Coding Conventions

**Analysis Date:** 2026-04-19

## Naming Patterns

**Files:**
- `snake_case.py` for all modules (e.g., `workflow.py`, `validation.py`, `planner.py`)
- Test files prefixed with `test_` matching their module (e.g., `test_workflow.py`)
- Single `conftest.py` at `tests/conftest.py` for shared fixtures

**Classes:**
- `PascalCase` for all classes (e.g., `WorkflowStateMachine`, `ValidationEngine`, `InMemoryStore`)
- Abstract base classes suffixed with their role (e.g., `StorageBackend`)
- Exception classes use descriptive `PascalCase` names indicating layer and kind (e.g., `PlannerRetryExhausted`, `FieldValidationError`)

**Functions and Methods:**
- `snake_case` for all functions and methods
- Private methods prefixed with single underscore (e.g., `_build_system_prompt`, `_apply_actions`, `_eval_single`)
- Section separator comments (`# ------------------------------------------------------------------`) used to divide public API from internal helpers within a class

**Variables:**
- `snake_case` for all local variables and instance attributes
- Private instance attributes prefixed with `_` (e.g., `self._policy`, `self._store`, `self._lock`)
- Module-level constants use `UPPER_SNAKE_CASE` with `frozenset` for allowlists (e.g., `_ALLOWED_ACTION_TYPES`, `_FORBIDDEN_UI_PATTERNS`)
- Sentinel constants use `UPPER_SNAKE_CASE` (e.g., `ALWAYS_HIDDEN`)

**Enums:**
- Class names in `PascalCase`, members in `UPPER_SNAKE_CASE`
- All enums inherit from both `str` and `Enum` to allow value comparison without `.value` access
  ```python
  class FieldType(str, Enum):
      TEXT = "text"
      NUMBER = "number"
  ```

**Type Hints:**
- Full type annotations on all function signatures
- Return type always annotated (including `-> None`)
- `from __future__ import annotations` at the top of every module for deferred evaluation
- Use `list[X]`, `dict[K, V]`, `tuple[A, B]` (lowercase generics — Python 3.11+)
- `Optional[X]` used rather than `X | None` in model fields; `X | None` used in function signatures
- `Any` imported from `typing` for truly dynamic values

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `black.toml`, or `ruff.toml`)
- Consistent 4-space indentation throughout
- Blank lines between methods; two blank lines between top-level definitions
- Lines stay within ~100 characters; no hard limit enforced by tooling

**Linting:**
- No ESLint/ruff/flake8 config detected; style is enforced by convention only

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first, in every file)
2. Standard library (`import re`, `import threading`, `import json`, etc.)
3. Third-party packages (`from pydantic import ...`, `import anthropic`, `import instructor`)
4. Internal package imports (`from schemakernel.exceptions import ...`, `from schemakernel.models import ...`)

**Pattern:**
- Explicit named imports only — no star imports
- Long import lists use multi-line parenthesized form
- Deferred imports used sparingly inside functions where circular import risk exists:
  ```python
  # In workflow.py submit_answer():
  from schemakernel.exceptions import FieldValidationError
  ```

**Path Aliases:**
- None — all internal imports use full `schemakernel.*` package paths

## Error Handling

**Exception Hierarchy:**
- All exceptions inherit from `SchemakernelError` (base in `schemakernel/exceptions.py`)
- Three sub-hierarchies matching architectural layers:
  - `PlannerError` → `PlannerResponseError`, `PlannerRetryExhausted`
  - `ValidationError` → `FieldValidationError`, `PolicyViolationError`, `PlannerOutputRejected`
  - `WorkflowError` → `TurnLimitExceeded`, `SessionNotFound`, `InvalidTransition`

**Pattern:**
- Methods return result objects (`ValidationResult`) rather than raising by default
- `raise_on_failure: bool = False` keyword-only parameter pattern used for optional raise behavior:
  ```python
  def validate_answer(self, field, value, *, raise_on_failure: bool = False) -> ValidationResult:
      ...
      if not result.valid and raise_on_failure:
          raise errors[0]
      return result
  ```
- External library exceptions caught broadly and re-raised as domain exceptions:
  ```python
  except Exception as exc:
      if type(exc).__name__ == "InstructorRetryException":
          raise PlannerRetryExhausted(...) from exc
      raise PlannerError(...) from exc
  ```
- `raise ... from exc` used consistently to preserve exception chains

**`FieldValidationError` constructor:**
```python
class FieldValidationError(ValidationError):
    def __init__(self, key: str, reason: str, value: Any = None) -> None:
        self.key = key
        self.reason = reason
        self.value = value
        super().__init__(f"Field '{key}': {reason}")
```

## Pydantic Model Conventions

**Configuration:**
- `model_config = ConfigDict(frozen=True)` for immutable value objects (rules, actions, responses, traces)
- `model_config = ConfigDict(frozen=False, validate_assignment=True)` for mutable state objects (`SchemaState`, `PolicyConfig`, `FieldDefinition`)
- `Field(default_factory=list)` and `Field(default_factory=dict)` for mutable defaults — never bare `[]` or `{}`

**Validation:**
- `@model_validator(mode="after")` used for cross-field validation
- Validators raise `ValueError` with descriptive messages matching test assertions
- Each validator has a descriptive method name explaining what it checks:
  ```python
  @model_validator(mode="after")
  def options_required_for_select(self) -> "FieldDefinition": ...

  @model_validator(mode="after")
  def complete_action_matches_status(self) -> "PlannerResponse": ...
  ```

**Deep Copy Pattern:**
- `.model_copy(deep=True)` used consistently when returning state from the store or applying actions, to prevent mutation of stored objects

## Module Design

**Exports:**
- `schemakernel/__init__.py` re-exports everything from submodules with an explicit `__all__` list
- Internal helpers and module-level constants prefixed with `_` are not exported

**Abstract Base Classes:**
- `StorageBackend` in `schemakernel/store.py` uses `ABC` + `@abstractmethod` with `...` body:
  ```python
  @abstractmethod
  def save_state(self, state: SchemaState) -> None: ...
  ```

**Factory Functions:**
- `create_workflow(policy: PolicyConfig) -> WorkflowStateMachine` in `schemakernel/workflow.py` acts as a convenience factory wiring all dependencies

## Comments

**When to Comment:**
- Section separator comments used to divide public API from private helpers within large classes
- Inline comments explain non-obvious logic (e.g., `# Detect instructor retry exhaustion by class name to avoid version coupling`)
- Numbered inline comments for multi-step validation sequences:
  ```python
  # 1. Allowlist: action types
  # 2. Allowlist: field types
  # 3. Allowlist: validator types
  ```

**Docstrings:**
- Not used — no function or class docstrings present in the codebase

## Function Design

**Size:**
- Short focused methods; larger orchestration methods (e.g., `run_planner_turn`, `validate_planner_response`) kept readable through numbered comments

**Parameters:**
- Keyword-only arguments used for boolean flags (e.g., `*, raise_on_failure: bool = False`)
- `**kw` only used in test helpers for forwarding to constructors

**Return Values:**
- Result objects (`ValidationResult`) for operations that can partially succeed
- Deep-copied model instances returned from store/workflow to prevent caller mutation
- `None` explicit return type annotated on mutating methods

**Concurrency:**
- `threading.Lock` used in `InMemoryStore` for all read/write operations:
  ```python
  with self._lock:
      self._states[state.session_id] = state.model_copy(deep=True)
  ```

---

*Convention analysis: 2026-04-19*
