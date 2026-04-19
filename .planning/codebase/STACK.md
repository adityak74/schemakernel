# Technology Stack

**Analysis Date:** 2026-04-19

## Languages

**Primary:**
- Python 3.11+ - All application code (requires-python = ">=3.11")

**Secondary:**
- None

## Runtime

**Environment:**
- CPython 3.11+ (tested on 3.14.2 locally)

**Package Manager:**
- pip / setuptools>=42 with wheel
- Build backend: `setuptools.build_meta`
- Lockfile: Not present (no `requirements.lock` or `pip.lock`)

## Frameworks

**Core:**
- Pydantic 2.10–2.x (`schemakernel/models.py`, `schemakernel/policy.py`) - Data modeling, schema validation, frozen/mutable model configs
- instructor 1.14–1.x (`schemakernel/planner.py`) - Structured LLM output extraction (wraps Anthropic/OpenAI clients)

**Testing:**
- pytest 8.3+ - Test runner; config in `pyproject.toml` under `[tool.pytest.ini_options]`
- pytest-asyncio 0.24+ - Async test support (`asyncio_mode = "auto"`)
- pytest-cov 5.0+ - Coverage reporting
- pytest-mock 3.14+ - Mocking utilities (used via `unittest.mock.MagicMock` in `tests/conftest.py`)

**Build/Dev:**
- setuptools - Package build
- wheel - Distribution format

## Key Dependencies

**Critical:**
- `anthropic>=0.40,<1` (`schemakernel/planner.py`) - Anthropic SDK; used to create `anthropic.Anthropic()` client, wrapped by instructor
- `openai>=1.40` (`schemakernel/planner.py`) - OpenAI SDK; used to create `openai.OpenAI()` client, wrapped by instructor
- `instructor>=1.14,<2` (`schemakernel/planner.py`) - Core structured output bridge; converts raw LLM clients to typed `PlannerResponse` via `instructor.from_anthropic()` / `instructor.from_openai()` and `create_with_completion()`
- `pydantic>=2.10,<3` (`schemakernel/models.py`, `schemakernel/policy.py`) - All domain models; enforces field constraints, frozen configs, model validators

**Infrastructure:**
- `python-dateutil>=2.9` - Date parsing utility available for date field validation
- `threading` (stdlib) - `InMemoryStore` uses `threading.Lock` for thread-safe state access (`schemakernel/store.py`)
- `uuid` (stdlib) - Session ID generation in `schemakernel/workflow.py`

## Configuration

**Environment:**
- LLM API keys are read from environment variables by the underlying SDKs at runtime:
  - `ANTHROPIC_API_KEY` - Required when `PolicyConfig.provider = "anthropic"` (default)
  - `OPENAI_API_KEY` - Required when `PolicyConfig.provider = "openai"`
- No `.env` file present in the repository

**Runtime Config:**
- All behavioral configuration is expressed through `PolicyConfig` (a Pydantic model at `schemakernel/policy.py`):
  - `provider`: `"anthropic"` | `"openai"` (default `"anthropic"`)
  - `model`: string (default `"claude-sonnet-4-6"`)
  - `temperature`: float 0.0–1.0 (default `0.2`)
  - `max_retries`: int 1–10 (default `3`)
  - `max_turns`: int 1–50 (default `10`)
  - `max_fields`: int 1–100 (default `20`)

**Build:**
- `pyproject.toml` - Single config file for project metadata, dependencies, and pytest options

## Platform Requirements

**Development:**
- Python 3.11+
- pip-installable; run `pip install -e .[dev]` for dev extras
- No Docker, no Makefile, no CI config present

**Production:**
- Pure Python library; no web server, no database, no container setup
- Consumers instantiate `WorkflowStateMachine` via `create_workflow(policy)` factory (`schemakernel/workflow.py`)
- Storage is pluggable via `StorageBackend` ABC (`schemakernel/store.py`); only `InMemoryStore` is provided out of the box

---

*Stack analysis: 2026-04-19*
