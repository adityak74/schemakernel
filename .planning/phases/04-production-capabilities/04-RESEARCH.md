# Phase 4: Production Capabilities - Research

**Researched:** 2025-02-13
**Domain:** Persistence, Observability, Compliance, Deployment
**Confidence:** HIGH

## Summary

This phase focuses on maturing SchemaKernel for enterprise and production environments. Key discoveries include using SQLAlchemy 2.0 with JSONB for flexible but typed session storage, adopting OpenTelemetry with specialized GenAI semantic conventions for LLM observability, and utilizing Microsoft Presidio for robust PII redaction.

**Primary recommendation:** Use SQLAlchemy with a custom Pydantic-to-JSONB TypeDecorator for Postgres, and implement a middleware-based redaction layer using Presidio to ensure data safety before persistence.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROD-01 | Cloud Storage Backends (Postgres/DynamoDB) | SQLAlchemy 2.0 `TypeDecorator` pattern and `boto3` session mapping verified. |
| PROD-02 | Prompt Versioning & A/B Testing | Immutable `PolicyVersion` schema and `PolicyAlias` (tagging) pattern identified. |
| PROD-03 | Telemetry & Audit Dashboards | `InstructorInstrumentor` (OpenTelemetry) and `structlog` confirmed as standard stack. |
| PROD-04 | Compliance Redaction Tooling | Microsoft Presidio identified as the gold standard for Python PII scrubbing. |
| PROD-05 | Enterprise Deployment Templates | Docker multi-stage builds and Helm v3/v4 charts with GPU resource management. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.49 | SQL toolkit and ORM | Industry standard for Python SQL; excellent JSONB support in 2.0. |
| boto3 | 1.34+ | AWS SDK for DynamoDB | Official AWS SDK; required for DynamoDB integration. |
| presidio-analyzer | 2.2.362 | PII detection | Microsoft-backed, extensible, and high-performance PII detection. |
| presidio-anonymizer | 2.2.362 | PII redaction/masking | Pairs with analyzer for flexible redaction strategies. |
| opentelemetry-sdk | 1.25.0+ | Observability framework | CNCF standard for distributed tracing and metrics. |
| openinference-instrumentation-instructor | 0.1.14 | LLM Instrumentation | Specifically designed to trace `instructor` and structured LLM calls. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| structlog | 24.1.0+ | Structured logging | For high-performance JSON logs suitable for ELK/Datadog. |
| alembic | 1.13.0+ | DB Migrations | When using SQLAlchemy to manage schema evolution. |
| pydantic-settings | 2.3.0+ | Environment config | For managing enterprise deployment secrets and configurations. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Microsoft Presidio | Custom Regex | Regex is faster but misses context and many PII types (high false negative rate). |
| OpenTelemetry | LangSmith/LangFuse | Specialized LLM platforms are easier to set up but cause vendor lock-in; OTel is vendor-neutral. |
| Helm | Kustomize | Kustomize is simpler for small setups; Helm is better for complex enterprise deployments with many parameters. |

## Architecture Patterns

### Recommended Project Structure
```
schemakernel/
├── storage/
│   ├── sql.py         # SQLAlchemy backend
│   └── dynamodb.py    # DynamoDB backend
├── telemetry/
│   ├── tracing.py     # OTel setup
│   └── logging.py     # structlog config
├── compliance/
│   └── redaction.py   # Presidio integration
└── deployment/        # Enterprise templates
    ├── docker/
    └── helm/
```

### Pattern 1: Pydantic-JSONB Mapping (SQLAlchemy)
**What:** Use a custom `TypeDecorator` to serialize/deserialize Pydantic models directly to Postgres JSONB.
**When to use:** Storing `SchemaState` and `PolicyConfig` in relational databases.
**Example:**
```python
# [VERIFIED: sqlalchemy docs / common patterns]
class PydanticJSONB(TypeDecorator):
    impl = JSONB
    def __init__(self, pydantic_model):
        super().__init__()
        self.pydantic_model = pydantic_model
    def process_bind_param(self, value, dialect):
        return value.model_dump(mode='json') if value else None
    def process_result_value(self, value, dialect):
        return self.pydantic_model.model_validate(value) if value else None
```

### Pattern 2: Immutable Prompt Versioning
**What:** Store policies in a `PolicyVersion` table with a `version_id`. Use a `PolicyAlias` table to map human-readable tags (e.g., `production`) to a specific `version_id`.
**When to use:** A/B testing and rollback capability for LLM policies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PII Detection | Custom Regex | Microsoft Presidio | PII is complex (dates, addresses, names) and requires NLP, not just regex. |
| LLM Tracing | Custom JSON logs | OpenTelemetry | OTel provides distributed tracing across services and standard semantic conventions. |
| AWS Auth | Manual Creds | boto3 / IAM | Standard AWS SDK handles credential rotation and IAM roles. |

## Common Pitfalls

### Pitfall 1: JSONB Change Detection
**What goes wrong:** Modifying a nested attribute in a Pydantic model doesn't trigger SQLAlchemy's dirty flag.
**How to avoid:** Treat Pydantic models as **immutable** in the ORM. Always replace the entire object using `model_copy(update=...)` or use SQLAlchemy's `MutableDict` extension.

### Pitfall 2: OTel Payload Size
**What goes wrong:** Including full LLM prompts/responses in traces can hit size limits in OTel collectors.
**How to avoid:** Use head-based sampling (e.g., 5%) for successful traces and 100% for errors. Use a collector-side redaction processor.

## Code Examples

### OTel Instrumentation for Instructor
```python
# Source: https://pypi.org/project/openinference-instrumentation-instructor/
from openinference.instrumentation.instructor import InstructorInstrumentor
from opentelemetry.sdk.trace import TracerProvider

InstructorInstrumentor().instrument(tracer_provider=TracerProvider())
# Instructor calls are now automatically traced with structured data.
```

### PII Redaction with Presidio
```python
# [VERIFIED: Microsoft Presidio Official Docs]
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

results = analyzer.analyze(text="My email is test@example.com", language="en")
redacted = anonymizer.anonymize(text="My email is test@example.com", analyzer_results=results)
# Output: "My email is <EMAIL_ADDRESS>"
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Deployment | ✓ | 29.1.3 | Build locally |
| Helm | Deployment | ✓ | v4.0.4 | Use `kubectl` manifests |
| Python | Runtime | ✓ | 3.14.2 | Use 3.11+ |
| Node.js | JS SDK (ref) | ✓ | v22.17.0 | — |
| Postgres | Persistence | ✗ | — | InMemoryStore |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3 |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/unit` |
| Full suite command | `pytest tests` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROD-01 | SQL/DynamoDB Persistence | Integration | `pytest tests/test_storage_backends.py` | ❌ Wave 0 |
| PROD-02 | Policy Versioning | Unit | `pytest tests/test_policy_versioning.py` | ❌ Wave 0 |
| PROD-03 | Telemetry Export | Integration | `pytest tests/test_telemetry.py` | ❌ Wave 0 |
| PROD-04 | PII Redaction | Unit | `pytest tests/test_redaction.py` | ❌ Wave 0 |

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | Pydantic validation for all storage inputs. |
| V8 Error Logging | Yes | Structured logging via `structlog`; PII redaction. |
| V12 File/Resources | Yes | Docker resource limits and Helm GPU constraints. |

### Known Threat Patterns for LLM Apps

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PII Leakage | Information Disclosure | Presidio Redaction Layer |
| Prompt Injection | Tampering | Output validation (already implemented in core) |
| Resource Exhaustion | Denial of Service | Docker/K8s resource limits |

## Sources

### Primary (HIGH confidence)
- `instructor` - [LLM structured output tracing]
- `sqlalchemy` - [JSONB and TypeDecorator docs]
- `presidio` - [Microsoft Presidio documentation]

### Secondary (MEDIUM confidence)
- OpenInference - [GenAI semantic conventions]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are mature and industry-standard.
- Architecture: HIGH - Patterns (TypeDecorator, Aliasing) are well-proven.
- Pitfalls: HIGH - Common issues with JSONB and OTel are well-documented.

**Research date:** 2025-02-13
**Valid until:** 2025-03-15
