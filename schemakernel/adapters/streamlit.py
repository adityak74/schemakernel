from __future__ import annotations

from typing import Any

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore

from schemakernel.exceptions import SessionNotFound
from schemakernel.models import (
    CompletionOutcome,
    FieldDefinition,
    FieldType,
    PlannerTrace,
    SchemaState,
)
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


class StreamlitFormAdapter:
    """
    Adapter to render SchemaKernel fields as native Streamlit widgets.
    """

    def _get_st(self) -> Any:
        if st is None:
            raise ImportError(
                "Streamlit is required to use StreamlitFormAdapter. "
                "Install it with `pip install streamlit`."
            )
        return st

    def _render_field(self, field: FieldDefinition, current_value: Any = None) -> Any:
        """
        Maps a FieldDefinition to a native Streamlit widget.
        """
        st = self._get_st()
        kwargs: dict[str, Any] = {
            "label": field.label,
            "help": field.description,
            "key": field.key,
        }

        # Value resolution: current_value (from state) > field.default
        val = current_value if current_value is not None else field.default

        if field.type == FieldType.NUMBER:
            return st.number_input(value=float(val) if val is not None else 0.0, **kwargs)

        if field.type == FieldType.INTEGER:
            return st.number_input(
                value=int(val) if val is not None else 0, step=1, format="%d", **kwargs
            )

        if field.type == FieldType.BOOLEAN:
            return st.checkbox(value=bool(val), **kwargs)

        if field.type == FieldType.DATE:
            return st.date_input(value=val, **kwargs)

        if field.type == FieldType.SELECT:
            options = field.options or []
            index = 0
            if val in options:
                index = options.index(val)
            return st.selectbox(options=options, index=index, **kwargs)

        if field.type == FieldType.MULTISELECT:
            options = field.options or []
            default = [v for v in (val or []) if v in options]
            return st.multiselect(options=options, default=default, **kwargs)

        if field.type == FieldType.TEXTAREA:
            return st.text_area(value=str(val) if val is not None else "", **kwargs)

        # TEXT, EMAIL, URL, PHONE fall through to text_input
        return st.text_input(value=str(val) if val is not None else "", **kwargs)

    def render_step(
        self,
        fields: list[FieldDefinition],
        current_answers: dict[str, Any],
        form_key: str = "sk_form",
        submit_label: str = "Continue",
    ) -> dict[str, Any] | None:
        """
        Renders a list of fields inside an st.form and returns answers on submit.

        Args:
            fields: List of FieldDefinition objects to render.
            current_answers: Dict of existing answers to pre-populate widgets.
            form_key: Unique key for the st.form.
            submit_label: Label for the submit button.

        Returns:
            A dict of answers if the form was submitted, otherwise None.
        """
        st = self._get_st()

        with st.form(key=form_key):
            for field in fields:
                self._render_field(field, current_answers.get(field.key))

            submitted = st.form_submit_button(submit_label)

            if submitted:
                # On submission, we collect the values from session state
                # because we used field.key as the widget key.
                answers = {}
                for field in fields:
                    if field.key in st.session_state:
                        answers[field.key] = st.session_state[field.key]
                return answers

        return None
