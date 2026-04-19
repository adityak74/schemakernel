# Directory Structure

**Analysis Date:** 2026-04-19

## Top-Level Layout

```
schemakernel/               # repo root
├── schemakernel/           # main Python package
│   ├── __init__.py         # public API surface (re-exports all symbols)
│   ├── exceptions.py       # exception hierarchy (SchemakernelError base)
│   ├── models.py           # all Pydantic domain models
│   ├── policy.py           # PolicyConfig and sub-models
│   ├── validation.py       # ValidationEngine
│   ├── planner.py          # PlannerClient (instructor/LLM wrapper)
│   ├── store.py            # StorageBackend ABC + InMemoryStore
│   └── workflow.py         # WorkflowStateMachine + create_workflow factory
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # shared fixtures, helper factories
│   ├── test_models.py      # model validation / invariant tests
│   ├── test_validation.py  # ValidationEngine unit tests
│   ├── test_planner.py     # PlannerClient tests (mocked LLM)
│   ├── test_store.py       # InMemoryStore tests
│   └── test_workflow.py    # WorkflowStateMachine integration tests
├── .planning/
│   ├── 01-product-requirements.md
│   ├── 02-core-engine-plan.md
│   └── codebase/           # this codebase map
├── pyproject.toml          # build config, deps, pytest settings
├── README.md
└── .gitignore
```

## Key File Locations

| Purpose | File |
|---------|------|
| Public import surface | `schemakernel/__init__.py` |
| All domain models | `schemakernel/models.py` |
| Operator configuration | `schemakernel/policy.py` |
| LLM integration | `schemakernel/planner.py` |
| Safety validation | `schemakernel/validation.py` |
| Session persistence | `schemakernel/store.py` |
| Session orchestration | `schemakernel/workflow.py` |
| Custom exceptions | `schemakernel/exceptions.py` |
| Test fixtures & factories | `tests/conftest.py` |
| Build & test config | `pyproject.toml` |

## Naming Conventions

**Files:** lowercase snake_case (`validation.py`, `test_workflow.py`)

**Classes:** PascalCase (`WorkflowStateMachine`, `PlannerClient`, `InMemoryStore`)

**Enums:** PascalCase class, UPPER_SNAKE members (`FieldType.TEXT`, `ActionType.ADD`)

**Functions/methods:** lowercase snake_case (`start_session`, `validate_answer`)

**Private methods:** leading underscore (`_apply_actions`, `_evaluate_condition`, `_build_prompt`)

**Constants/sentinels:** UPPER_SNAKE (`ALWAYS_HIDDEN`)

**Test files:** `test_<module>.py` (mirrors source module name)

**Fixtures:** noun-phrase snake_case (`minimal_field`, `mock_planner`, `in_memory_store`)

## Where to Add New Code

| What | Where |
|------|-------|
| New field type | `FieldType` enum in `models.py`; update `ValidationEngine` coercion in `validation.py` |
| New validator type | `ValidatorType` enum + `ValidatorRule` in `models.py`; add check in `ValidationEngine.validate_answer` |
| New planner action | `ActionType` enum in `models.py`; handle in `WorkflowStateMachine._apply_actions` in `workflow.py` |
| New storage backend | New class implementing `StorageBackend` ABC from `store.py` |
| New policy config option | Add field to `PolicyConfig` in `policy.py`; thread through planner/validation as needed |
| New exception type | Add to `exceptions.py` under appropriate parent |
| New public symbol | Add to `schemakernel/__init__.py` |

---

*Structure analysis: 2026-04-19*
