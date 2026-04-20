from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from schemakernel.adapters.streamlit import StreamlitSessionStore
from schemakernel.exceptions import SessionNotFound
from schemakernel.models import (
    CompletionOutcome,
    CompletionStatus,
    PlannerTrace,
    SchemaState,
    WorkflowStage,
)


class MockSessionState(dict):
    pass


def make_state(sid="s1") -> SchemaState:
    return SchemaState(session_id=sid)


class TestStreamlitSessionStore:
    @pytest.fixture
    def mock_st(self):
        with patch("schemakernel.adapters.streamlit.st") as mock_st:
            mock_st.session_state = MockSessionState()
            yield mock_st

    def test_save_and_load_state(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        state = make_state()
        state.stage = WorkflowStage.COLLECTING
        store.save_state(state)

        # Check if it was saved in session_state with prefix
        assert "test_s1_state" in mock_st.session_state
        assert isinstance(mock_st.session_state["test_s1_state"], SchemaState)

        loaded = store.load_state("s1")
        assert loaded.session_id == "s1"
        assert loaded.stage == WorkflowStage.COLLECTING
        # Ensure deep copies are used for retrieval
        assert loaded is not mock_st.session_state["test_s1_state"]

    def test_load_missing_raises(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        with pytest.raises(SessionNotFound):
            store.load_state("nope")

    def test_save_state_deep_copies(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        state = make_state()
        store.save_state(state)
        
        # Modify original state
        state.answers["x"] = 42
        
        # Loaded state should not have the modification
        loaded = store.load_state("s1")
        assert "x" not in loaded.answers
        # Mocked state should also not have the modification if deep copied on save
        assert "x" not in mock_st.session_state["test_s1_state"].answers

    def test_save_and_list_traces(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        trace = PlannerTrace(session_id="s1", turn=0, raw_response={}, validated=True)
        store.save_trace(trace)
        
        assert "test_s1_traces" in mock_st.session_state
        assert len(mock_st.session_state["test_s1_traces"]) == 1
        
        traces = store.list_traces("s1")
        assert len(traces) == 1
        assert traces[0].turn == 0
        # Ensure deep copies
        assert traces[0] is not mock_st.session_state["test_s1_traces"][0]

    def test_list_traces_missing_session_empty(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        assert store.list_traces("nobody") == []

    def test_save_and_load_outcome(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        outcome = CompletionOutcome(
            session_id="s1",
            status=CompletionStatus.COMPLETE,
            final_answers={},
            final_schema={},
            rationale=["done"],
        )
        store.save_outcome(outcome)
        
        assert "test_s1_outcome" in mock_st.session_state
        
        loaded = store.load_outcome("s1")
        assert loaded.status == CompletionStatus.COMPLETE
        # Ensure deep copies
        assert loaded is not mock_st.session_state["test_s1_outcome"]

    def test_load_outcome_missing_raises(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        with pytest.raises(SessionNotFound):
            store.load_outcome("nope")

    def test_delete_state(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        store.save_state(make_state("s1"))
        store.save_trace(PlannerTrace(session_id="s1", turn=0, raw_response={}, validated=True))
        store.save_outcome(CompletionOutcome(
            session_id="s1", status=CompletionStatus.COMPLETE, 
            final_answers={}, final_schema={}, rationale=[]
        ))
        
        assert "test_s1_state" in mock_st.session_state
        assert "test_s1_traces" in mock_st.session_state
        assert "test_s1_outcome" in mock_st.session_state
        
        store.delete_state("s1")
        
        assert "test_s1_state" not in mock_st.session_state
        assert "test_s1_traces" not in mock_st.session_state
        assert "test_s1_outcome" not in mock_st.session_state

    def test_type_mismatch_raises_typeerror(self, mock_st):
        store = StreamlitSessionStore(key_prefix="test_")
        mock_st.session_state["test_s1_state"] = "not a state object"
        
        with pytest.raises(TypeError, match="Expected SchemaState"):
            store.load_state("s1")

    def test_streamlit_missing_raises_importerror(self):
        with patch("schemakernel.adapters.streamlit.st", None):
             store = StreamlitSessionStore()
             with pytest.raises(ImportError, match="Streamlit is required"):
                 store.save_state(make_state())
