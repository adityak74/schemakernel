# Project: SchemaKernel

## Overview
SchemaKernel is a developer platform for building adaptive forms where a Large Language Model (LLM) acts as a constrained planner. It decides which fields to ask, how to validate responses, and when to ask follow-up questions, while the host runtime handles deterministic rendering, validation enforcement, and persistence.

## Vision
To provide a shared orchestration layer that allows developers to define form policies and exception rules once, running them through a structured planner that emits safe, typed schema updates for multiple runtimes (initially Python/Streamlit and later JavaScript/SurveyJS).

## Target Audiences
- **Python Developers:** Building internal workflows and intake apps using Streamlit.
- **JavaScript Developers:** Integrating adaptive form logic into schema-driven UI systems like SurveyJS.

## Core Principles
1. **Schema-First:** The canonical field schema is the source of truth.
2. **Planner-Constrained:** LLM actions are strictly limited to allowed operations.
3. **Runtime-Deterministic:** Enforcement and rendering are handled by the host environment.
4. **Auditability:** Every change is traceable and explainable.

## Success Criteria
- Reliable structured output from LLMs via `instructor`.
- Zero-leakage of unvalidated LLM output to the UI.
- Seamless integration with Streamlit's `session_state` and `st.form`.
- Parity in policy definition across Python and JavaScript runtimes.
