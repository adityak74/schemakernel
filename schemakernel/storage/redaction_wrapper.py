from __future__ import annotations

from typing import List, Optional

from schemakernel.compliance.redaction import RedactionEngine
from schemakernel.models import CompletionOutcome, PlannerTrace, SchemaState
from schemakernel.store import StorageBackend


class RedactingStorageWrapper(StorageBackend):
    """
    Storage wrapper that redacts PII before persisting data.
    Uses a decorator pattern to wrap any StorageBackend.
    """

    def __init__(
        self, backend: StorageBackend, entities: Optional[List[str]] = None
    ) -> None:
        """
        Initialize the redacting storage wrapper.

        Args:
            backend: The storage backend to wrap.
            entities: Optional list of PII entities to redact.
        """
        self.backend = backend
        self.redactor = RedactionEngine(entities=entities)

    def save_state(self, state: SchemaState) -> None:
        """
        Redact answers and audit_log before saving state.
        """
        redacted_state = state.model_copy(deep=True)
        redacted_state.answers = self.redactor.redact_data(redacted_state.answers)
        if redacted_state.audit_log:
            redacted_state.audit_log = self.redactor.redact_data(redacted_state.audit_log)

        self.backend.save_state(redacted_state)

    def load_state(self, session_id: str) -> SchemaState:
        """Delegate to wrapped backend."""
        return self.backend.load_state(session_id)

    def delete_state(self, session_id: str) -> None:
        """Delegate to wrapped backend."""
        self.backend.delete_state(session_id)

    def save_trace(self, trace: PlannerTrace) -> None:
        """
        Redact raw_response before saving trace.
        """
        redacted_raw_response = self.redactor.redact_data(trace.raw_response)
        redacted_trace = trace.model_copy(update={"raw_response": redacted_raw_response})
        self.backend.save_trace(redacted_trace)

    def list_traces(self, session_id: str) -> list[PlannerTrace]:
        """Delegate to wrapped backend."""
        return self.backend.list_traces(session_id)

    def save_outcome(self, outcome: CompletionOutcome) -> None:
        """
        Redact final_answers before saving outcome.
        """
        redacted_final_answers = self.redactor.redact_data(outcome.final_answers)
        redacted_outcome = outcome.model_copy(
            update={"final_answers": redacted_final_answers}
        )
        self.backend.save_outcome(redacted_outcome)

    def load_outcome(self, session_id: str) -> CompletionOutcome:
        """Delegate to wrapped backend."""
        return self.backend.load_outcome(session_id)
