# Product Requirements Document: SchemaKernel

## Overview

SchemaKernel is a developer platform for building adaptive forms in which a large language model decides what fields to ask, how to validate responses, and when to ask follow-up questions. The platform does not generate HTML. Instead, it produces structured field definitions, validation rules, branching logic, and completion signals that are consumed by deterministic UI renderers in Python and JavaScript.

SchemaKernel targets two primary developer audiences: Python developers who want a Streamlit UI experience and JavaScript developers who want to plug the engine into schema-driven form systems. Streamlit forms batch user input submission, and `st.session_state` persists workflow state across reruns, which makes Streamlit suitable for adaptive multi-step forms.

The canonical open-source repository name is `schemakernel`. The product name is **SchemaKernel**, while package naming may vary by ecosystem, such as `schemakernel` on PyPI and npm if available.

## Problem Statement

Traditional forms are static, ask too many irrelevant questions, and cannot adapt their flow based on partial responses. Schema-driven form systems solve rendering and validation, but they usually leave dynamic questioning and exception handling to application-specific logic.

LLMs can reason over prior answers and domain policies, but they are not reliable enough to directly control UI unless their outputs are constrained to typed structured objects and validated before execution. Instructor addresses this by producing Pydantic-validated structured outputs with retries and provider flexibility.

## Vision

SchemaKernel provides a shared orchestration layer that lets developers define form policy, baseline questions, exception rules, and completion criteria once, then run that policy through a structured planner that emits safe schema updates for multiple runtimes. The LLM acts as a planner, while the runtime remains deterministic and auditable.

The product should feel like a schema execution kernel for adaptive forms rather than a chatbot or page builder. The LLM plans field additions and validation updates, while the host runtime handles rendering, interaction, storage, and enforcement.

## Target Users

### Python users

Python users are developers, data teams, and domain experts who want to build internal workflows, intake apps, decision support tools, and guided collection experiences quickly in Streamlit. Streamlit supports both forms and per-session state, which makes it well suited for adaptive workflows built around reruns and staged submission.

### JavaScript users

JavaScript users are front-end and full-stack developers who want adaptive forms in React, Next.js, Node.js, and similar stacks. JSON-driven form systems such as SurveyJS already support schema-based rendering and validation, making them natural integration targets for SchemaKernel.

## Product Goals

- Provide a single cross-language schema orchestration core for Python and JavaScript.
- Allow developers to define rules in a system policy instead of hardcoding form branching in UI code.
- Ensure the LLM only emits structured schema changes and completion metadata, not HTML or executable UI code.
- Support adaptive follow-up questions based on missing information, exceptions, contradictions, risk flags, and threshold conditions.
- Keep rendering deterministic so validation, accessibility, and persistence remain under developer control.
- Support hosted and local model providers when structured outputs can be enforced reliably.

## Non-Goals

- Generating raw HTML, CSS, or a full web front end.
- Replacing mature schema-rendering libraries in JavaScript.
- Acting as a general-purpose chatbot UX.
- Shipping domain-specific legal, medical, or compliance policies out of the box.

## Core Concept

SchemaKernel operates as an adaptive form loop. The runtime sends the current schema, prior answers, workflow stage, and policy to the planner. The planner returns a typed response that may add fields, modify validators, mark fields required, request clarification, or indicate completion. The runtime validates this response, merges it into the canonical schema, renders the next step, captures new answers, and repeats.

This model depends on a strict schema contract and a deterministic enforcement layer. Structured output libraries such as Instructor and schema-driven form systems such as SurveyJS provide strong precedent for this split between planning and rendering.

## Product Principles

- **Schema first:** The source of truth is the canonical field schema, not UI markup.
- **Planner constrained:** The LLM may propose only allowed actions and allowed field definitions.
- **Runtime deterministic:** Validation and rendering are executed by the runtime, not improvised by the model.
- **Cross-runtime parity:** Python and JavaScript should share the same conceptual model and policy format.
- **Auditability:** Every field addition and rule change should be explainable and traceable.

## User Stories

### Shared

- As a developer, SchemaKernel should let a system policy define baseline questions, exception rules, prohibited questions, escalation triggers, and stop conditions.
- As a developer, SchemaKernel should let the LLM emit field keys, types, validation metadata, and branching conditions while the renderer chooses the actual UI control.
- As a developer, SchemaKernel should support validation such as required, min, max, enum, regex, text length, date bounds, and flags like whether negative numbers are allowed.
- As an end user, the form should ask only relevant follow-up questions.
- As an operator, the system should preserve why a field was added or updated.

### Python / Streamlit

- As a Python developer, SchemaKernel should integrate naturally with `st.form` for submission batching.
- As a Python developer, SchemaKernel should preserve answers, generated schema, and planner state using `st.session_state` across reruns.
- As a Python developer, SchemaKernel should make it easy to prototype adaptive workflows in one file before moving to production infrastructure.

### JavaScript

- As a JavaScript developer, SchemaKernel should emit JSON-friendly schemas that can be rendered in browser or server-driven applications.
- As a JavaScript developer, SchemaKernel should support integration with schema-driven renderers and custom field registries.
- As a JavaScript developer, SchemaKernel should support server-side orchestration for prompt confidentiality and policy enforcement.

## Functional Requirements

### Canonical schema model

SchemaKernel must define a canonical schema contract that is independent of the UI framework. A field must support at least `key`, `type`, `label`, `description`, `required`, `default`, `validators`, `ui_props`, `visible_if`, `ask_if_missing`, `follow_up_if`, and `priority`.

SchemaKernel must support both full-schema generation and incremental schema patches. Incremental patches reduce token usage and simplify diffing when the form evolves after each answer.

### Planner contract

The planner must return a typed response that includes:

- `actions`: add, update, remove, require, hide, show, reorder, complete, escalate
- `fields`: new or updated field definitions
- `rationale`: concise reason codes for audit logs
- `completion_status`: in_progress, needs_clarification, complete, escalate
- `next_prompt_context`: optional internal planner context for the next turn

Planner output must be validated before any changes are applied.

### Validation engine

The runtime must enforce validation deterministically. Supported validation must include required, type checks, min/max, minLength/maxLength, pattern, enum membership, numeric sign rules, date bounds, and custom domain validators.

The runtime must reject invalid planner output, support retry policies, and record validation failures in logs.

### Adaptive branching

SchemaKernel must support conditional follow-up questions triggered by:

- missing critical data
- contradictory answers
- high-risk or exception answers
- selected options
- threshold crossings on numeric answers
- external rules-engine results

The planner must be able to signal "complete" when enough information has been gathered for the target workflow.

### Policy configuration

Developers must be able to configure a policy with:

- baseline questions
- glossary and domain hints
- exception rules
- prohibited topics
- escalation thresholds
- completion criteria
- reasoning style guidance
- token and latency guidance

The product should separate policy definition from runtime answer state so policy can be versioned and reused.

### Rendering adapters

#### Streamlit adapter

The Streamlit adapter must render supported fields using Streamlit widgets and optionally group them into `st.form` sections for submit-based progression. It must use `st.session_state` to persist answers, current schema, planner state, workflow stage, and audit metadata across reruns.

#### JavaScript adapter

The JavaScript adapter must produce renderer-friendly JSON that can map canonical field types to host widgets. It should integrate with JSON-schema-oriented systems such as SurveyJS and support conditional visibility, custom components, and sanitized submission handling.

### Observability

SchemaKernel must log planner requests and planner outputs in a structured, redactable format. Logs should include model, schema version, policy version, field diffs, validation failures, completion state, and timestamps.

### Persistence

SchemaKernel should provide storage abstractions for sessions, answer history, final schema, planner trace, and completion outcome. Implementations may include in-memory stores, files, databases, and cloud-backed backends.

## System Architecture

### Components

1. Policy manager
2. Planner client
3. Canonical schema model
4. Validation engine
5. Workflow state machine
6. Streamlit adapter
7. JavaScript adapter
8. Persistence layer
9. Audit and telemetry layer

### Workflow

1. Load the policy and base schema.
2. Render baseline questions.
3. Collect answers.
4. Send policy, schema, and answers to the planner.
5. Validate planner output.
6. Apply schema patch.
7. Render next questions or finish.
8. Persist state and audit logs.

## Safety Requirements

SchemaKernel must prevent the planner from emitting unsupported field types, arbitrary code, raw HTML, or executable validators. All planner outputs must be checked against allowlists for action types, field types, and validation types before being applied.

SchemaKernel should support escalation workflows for sensitive use cases. High-risk prompts or answers may require manual review before more questions are shown or before submission is accepted.

## Security and Privacy

Policy prompts may contain sensitive internal logic, so JavaScript deployments should support server-side planning as the default architecture. Session and telemetry systems must support redaction of personally identifiable information and configurable retention policies.

## Release Plan

### Phase 1: Core engine

Deliver canonical schema models, planner contracts, validation engine, policy model, and in-memory storage. Ship Python first with a reference implementation based on Instructor-compatible structured outputs.

### Phase 2: Streamlit adapter

Deliver first-party Streamlit support using `st.form` and `st.session_state`, plus example apps for intake, screening, and guided workflows.

### Phase 3: JavaScript SDK

Deliver a TypeScript SDK with renderer adapters and examples for a schema-driven web application stack such as SurveyJS.

### Phase 4: Production capabilities

Add persistence backends, replay tooling, prompt-version A/B testing, telemetry dashboards, governance controls, and enterprise deployment features.

## Open Questions

- Should SchemaKernel expose JSON Schema directly or maintain a richer canonical schema with export adapters?
- Should branching be planner-only, rules-engine-only, or hybrid?
- How much rationale should be stored for audit without storing hidden reasoning content?
- Which JavaScript renderer should be the first official integration?
- Should scoring, summarization, and downstream action triggers be first-class outputs in v1 or post-v1?
