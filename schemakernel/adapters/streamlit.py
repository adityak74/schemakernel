from __future__ import annotations

from typing import Any

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore

from schemakernel.exceptions import SessionNotFound
from schemakernel.models import CompletionOutcome, PlannerTrace, SchemaState
from schemakernel.store import StorageBackend


class StreamlitSessionStore(StorageBackend):
    """
    Persistence backend using Streamlit's st.session_state.

    Useful for single-user Streamlit apps or when external DB is not available.
    States are prefixed to avoid collisions with other session state keys.
    """

    def __init__(self, key_prefix: str = "sk_") -> None:
        self.key_prefix = key_prefix

    def _get_st(self) -> Any:
        if st is None:
            raise ImportError(
                "Streamlit is required to use StreamlitSessionStore. "
                "Install it with `pip install streamlit`."
            )
        return st

    def _get_key(self, session_id: str, suffix: str) -> str:
        return f"{self.key_prefix}{session_id}_{suffix}"

    def save_state(self, state: SchemaState) -> None:
        st = self._get_st()
        key = self._get_key(state.session_id, "state")
        st.session_state[key] = state.model_copy(deep=True)

    def load_state(self, session_id: str) -> SchemaState:
        st = self._get_st()
        key = self._get_key(session_id, "state")
        if key not in st.session_state:
            raise SessionNotFound(f"Session state '{session_id}' not found in st.session_state")
        state = st.session_state[key]
        if not isinstance(state, SchemaState):
            # This could happen if something else wrote to our key
            raise TypeError(f"Expected SchemaState at {key}, found {type(state)}")
        return state.model_copy(deep=True)

    def delete_state(self, session_id: str) -> None:
        st = self._get_st()
        keys_to_delete = [
            self._get_key(session_id, "state"),
            self._get_key(session_id, "traces"),
            self._get_key(session_id, "outcome"),
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    def save_trace(self, trace: PlannerTrace) -> None:
        st = self._get_st()
        key = self._get_key(trace.session_id, "traces")
        if key not in st.session_state:
            st.session_state[key] = []
        st.session_state[key].append(trace.model_copy(deep=True))

    def list_traces(self, session_id: str) -> list[PlannerTrace]:
        st = self._get_st()
        key = self._get_key(session_id, "traces")
        traces = st.session_state.get(key, [])
        return [t.model_copy(deep=True) for t in traces]

    def save_outcome(self, outcome: CompletionOutcome) -> None:
        st = self._get_st()
        key = self._get_key(outcome.session_id, "outcome")
        st.session_state[key] = outcome.model_copy(deep=True)

    def load_outcome(self, session_id: str) -> CompletionOutcome:
        st = self._get_st()
        key = self._get_key(session_id, "outcome")
        if key not in st.session_state:
            raise SessionNotFound(f"No outcome for session '{session_id}' in st.session_state")
        outcome = st.session_state[key]
        if not isinstance(outcome, CompletionOutcome):
            raise TypeError(f"Expected CompletionOutcome at {key}, found {type(outcome)}")
        return outcome.model_copy(deep=True)
