from __future__ import annotations

import pytest

from schemakernel.exceptions import SessionNotFound
from schemakernel.models import (
    CompletionOutcome,
    CompletionStatus,
    FieldDefinition,
    FieldType,
    PlannerTrace,
    SchemaState,
    WorkflowStage,
)
from schemakernel.store import InMemoryStore


def make_state(sid="s1") -> SchemaState:
    return SchemaState(session_id=sid)


class TestInMemoryStore:
    def test_save_and_load_state(self):
        store = InMemoryStore()
        state = make_state()
        state.stage = WorkflowStage.COLLECTING
        store.save_state(state)
        loaded = store.load_state("s1")
        assert loaded.session_id == "s1"
        assert loaded.stage == WorkflowStage.COLLECTING

    def test_load_missing_raises(self):
        store = InMemoryStore()
        with pytest.raises(SessionNotFound):
            store.load_state("nope")

    def test_save_state_deep_copies(self):
        store = InMemoryStore()
        state = make_state()
        store.save_state(state)
        state.answers["x"] = 42
        loaded = store.load_state("s1")
        assert "x" not in loaded.answers

    def test_save_and_list_traces(self):
        store = InMemoryStore()
        trace = PlannerTrace(session_id="s1", turn=0, raw_response={}, validated=True)
        store.save_trace(trace)
        traces = store.list_traces("s1")
        assert len(traces) == 1
        assert traces[0].turn == 0

    def test_list_traces_missing_session_empty(self):
        store = InMemoryStore()
        assert store.list_traces("nobody") == []

    def test_save_and_load_outcome(self):
        store = InMemoryStore()
        outcome = CompletionOutcome(
            session_id="s1",
            status=CompletionStatus.COMPLETE,
            final_answers={},
            final_schema={},
            rationale=["done"],
        )
        store.save_outcome(outcome)
        loaded = store.load_outcome("s1")
        assert loaded.status == CompletionStatus.COMPLETE

    def test_load_outcome_missing_raises(self):
        store = InMemoryStore()
        with pytest.raises(SessionNotFound):
            store.load_outcome("nope")

    def test_delete_state(self):
        store = InMemoryStore()
        store.save_state(make_state())
        store.delete_state("s1")
        with pytest.raises(SessionNotFound):
            store.load_state("s1")
