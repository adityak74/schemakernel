# Phase 03: JavaScript SDK - Research

**Researched:** 2025-03-24
**Domain:** TypeScript, SurveyJS, Node.js/Express, Multi-runtime Parity
**Confidence:** HIGH

## Summary

Phase 3 focuses on extending SchemaKernel into the JavaScript/TypeScript ecosystem. The primary deliverables are a canonical TypeScript SDK that mirrors the Python core's logic, a SurveyJS adapter for frontend rendering, and Express middleware for backend orchestration. 

A critical requirement is **Multi-runtime Parity**, ensuring that the same schema and answers produce identical validation results and state transitions in both Python and JavaScript. This will be achieved through a shared suite of JSON-based "parity vectors" used by both `pytest` and `vitest`.

**Primary recommendation:** Use `zod` for model definitions and `instructor-js` for the planner client to maintain maximum feature parity with the Python `pydantic` and `instructor` implementation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typescript` | ^5.0.0 | Language | Type safety and DX |
| `zod` | ^3.23.0 | Validation | Industry standard for TS; Pydantic equivalent |
| `@instructor-ai/instructor` | ^1.7.0 | Structured LLM | Parity with Python Instructor |
| `openai` | ^4.0.0 | LLM Client | Required by Instructor |
| `dayjs` | ^1.11.0 | Date Handling | Lightweight parity with Python `dateutil` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `express` | ^4.19.0 | Middleware | Required for orchestration layer |
| `survey-core` | ^2.5.0 | Form Library | Rendering target for adapter |
| `vitest` | ^1.6.0 | Testing | Fast, TS-native test runner |
| `tsup` | ^8.0.0 | Build Tool | Zero-config library bundling |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `zod` | `typebox` | Faster but less feature-rich for complex refinements |
| `dayjs` | `date-fns` | Excellent but `dayjs` has a more `dateutil`-like API |
| `vitest` | `jest` | `jest` requires more boilerplate for TS/ESM |

**Installation:**
```bash
npm install zod @instructor-ai/instructor openai dayjs survey-core express
npm install -D typescript vitest tsup @types/express
```

## Architecture Patterns

### Recommended Project Structure
```
js-sdk/
├── src/
│   ├── index.ts          # Main entry point
│   ├── models.ts         # Zod schemas (mirror models.py)
│   ├── workflow.ts       # State Machine (mirror workflow.py)
│   ├── validation.ts     # Validation Engine (mirror validation.py)
│   ├── planner.ts        # Planner Client (mirror planner.py)
│   ├── store.ts          # Storage interfaces & InMemoryStore
│   ├── adapters/
│   │   └── surveyjs.ts   # SurveyJS JSON generator
│   └── middleware/
│       └── express.ts    # Orchestration middleware
├── tests/
│   ├── unit/             # Local unit tests
│   └── parity/           # Parity tests using shared vectors
└── vectors/              # Symlink or shared folder with Python tests
```

### Pattern 1: Recursive Expression Mapping
To map `ConditionalLogic` to SurveyJS `visibleIf` strings, use a recursive visitor pattern to ensure nested `and`/`or` groups are correctly parenthesized.

### Anti-Patterns to Avoid
- **Implicit Coercion:** JS is loose with types. Use Zod's `.coerce` carefully or manually coerce to match Python's `_coerce` logic exactly.
- **Regex Divergence:** Python's `re.fullmatch` must be emulated in JS using `new RegExp(`^${pattern}$`)`. Be aware of flag differences (e.g., `s` flag).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM | Custom Prompting | `instructor-js` | Ensures identical JSON extraction logic as Python. |
| Form Rendering | Custom UI Components | `SurveyJS` | Production-grade form features (paging, validation, logic). |
| Date Parsing | Native `Date` | `dayjs` | Native `Date` is notoriously buggy with ISO strings and timezones. |
| Type Validation | Manual `if` checks | `zod` | Provides `infer` for TS types and complex refinements. |

## Common Pitfalls

### Pitfall 1: Date Parity
**What goes wrong:** Python's `datetime.utcnow()` and JS `new Date()` might serialize differently in JSON (e.g. `Z` suffix vs no suffix).
**How to avoid:** Standardize on ISO 8601 strings in shared JSON vectors and use `dayjs(str).toISOString()` for all storage/comparison.

### Pitfall 2: SurveyJS Expression Syntax
**What goes wrong:** Mapping `ConditionOperator.IN` to SurveyJS.
**How to avoid:** SurveyJS uses `anyof` for array membership. Use `{field} anyof ['val1', 'val2']`.

### Pitfall 3: Turn Counter Inconsistency
**What goes wrong:** Off-by-one errors when porting `turn_count` logic.
**How to avoid:** Use the exact same increment points as `workflow.py`.

## Code Examples

### Zod Model Parity
```typescript
import { z } from 'zod';

export const FieldType = z.enum([
  'text', 'number', 'integer', 'boolean', 'date', 'datetime',
  'select', 'multiselect', 'email', 'url', 'phone', 'textarea'
]);

export const FieldDefinitionSchema = z.object({
  key: z.string().regex(/^[a-zA-Z_][a-zA-Z0-9_]{0,63}$/),
  type: FieldType,
  label: z.string().min(1).max(200),
  description: z.string().max(1000).optional(),
  required: z.boolean().default(false),
  options: z.array(z.string()).optional(),
  // ... other fields
}).refine(data => {
  if (['select', 'multiselect'].includes(data.type) && !data.options) {
    return false;
  }
  return true;
}, { message: "Options required for select/multiselect" });
```

### SurveyJS Adapter logic
```typescript
export function mapToSurveyJS(state: SchemaState) {
  return {
    pages: [{
      elements: state.field_order.map(key => {
        const field = state.fields[key];
        // ... map FieldType to SurveyJS type ...
        // ... map ConditionalLogic to visibleIf string ...
      })
    }]
  };
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 1.6+ |
| Config file | `vitest.config.ts` |
| Quick run command | `npm test` |
| Full suite command | `npm run test:full` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JS-MOD | Model Parity | Parity | `vitest tests/parity/models.test.ts` | ❌ Wave 0 |
| JS-VAL | Validation Parity | Parity | `vitest tests/parity/validation.test.ts` | ❌ Wave 0 |
| JS-SUR | SurveyJS Adapter | Unit | `vitest tests/unit/surveyjs.test.ts` | ❌ Wave 0 |
| JS-MID | Express Middleware | Integration | `vitest tests/unit/middleware.test.ts` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] Create `vectors/` directory for shared JSON test cases.
- [ ] Implement `tests/parity/vector_loader.ts` to iterate through JSON files.
- [ ] Add `pytest` markers in Python to run against the same `vectors/`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | `zod` schema enforcement on all API inputs |
| V5.1.3 Sanitization | Yes | Port `_FORBIDDEN_UI_PATTERNS` to JS SDK |
| V13 API Security | Yes | Ensure Middleware handles session-id securely |

### Known Threat Patterns for JS/Node

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prototype Pollution | Tampering | Use `Map` or `Object.create(null)` for state stores |
| Prompt Injection | Information Disclosure | Validate LLM rationale against prohibited topics policy |
| XSS in Forms | Tampering | Ensure `ui_props` are sanitized before mapping to SurveyJS |

## Sources

### Primary (HIGH confidence)
- `surveyjs.io` documentation for JSON schema and expressions.
- `instructor-ai.github.io/instructor-js/` for structured output patterns.
- `zod.dev` for schema refinement patterns.
- `schemakernel/models.py` for canonical source of truth.

### Secondary (MEDIUM confidence)
- Community patterns for "Parity Testing" between Python and JS (JSON vectors).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are mature and have direct Python equivalents.
- Architecture: HIGH - Mirroring Python structure is a proven path for parity.
- Pitfalls: MEDIUM - Subtle differences in Regex/Date behavior may still arise.

**Research date:** 2025-03-24
**Valid until:** 2025-04-24
