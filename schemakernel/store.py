from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from schemakernel.exceptions import SessionNotFound
from schemakernel.models import CompletionOutcome, PlannerTrace, SchemaState


class StorageBackend(ABC):
    @abstractmethod
    def save_state(self, state: SchemaState) -> None: ...

    @abstractmethod
    def load_state(self, session_id: str) -> SchemaState: ...

    @abstractmethod
    def delete_state(self, session_id: str) -> None: ...

    @abstractmethod
    def save_trace(self, trace: PlannerTrace) -> None: ...

    @abstractmethod
    def list_traces(self, session_id: str) -> list[PlannerTrace]: ...

    @abstractmethod
    def save_outcome(self, outcome: CompletionOutcome) -> None: ...

    @abstractmethod
    def load_outcome(self, session_id: str) -> CompletionOutcome: ...


class InMemoryStore(StorageBackend):
    def __init__(self) -> None:
        self._states: dict[str, SchemaState] = {}
        self._traces: dict[str, list[PlannerTrace]] = {}
        self._outcomes: dict[str, CompletionOutcome] = {}
        self._lock = threading.Lock()

    def save_state(self, state: SchemaState) -> None:
        with self._lock:
            self._states[state.session_id] = state.model_copy(deep=True)

    def load_state(self, session_id: str) -> SchemaState:
        with self._lock:
            if session_id not in self._states:
                raise SessionNotFound(f"Session '{session_id}' not found")
            return self._states[session_id].model_copy(deep=True)

    def delete_state(self, session_id: str) -> None:
        with self._lock:
            self._states.pop(session_id, None)
            self._traces.pop(session_id, None)
            self._outcomes.pop(session_id, None)

    def save_trace(self, trace: PlannerTrace) -> None:
        with self._lock:
            self._traces.setdefault(trace.session_id, []).append(trace)

    def list_traces(self, session_id: str) -> list[PlannerTrace]:
        with self._lock:
            return list(self._traces.get(session_id, []))

    def save_outcome(self, outcome: CompletionOutcome) -> None:
        with self._lock:
            self._outcomes[outcome.session_id] = outcome

    def load_outcome(self, session_id: str) -> CompletionOutcome:
        with self._lock:
            if session_id not in self._outcomes:
                raise SessionNotFound(
                    f"No outcome for session '{session_id}'"
                )
            return self._outcomes[session_id]
