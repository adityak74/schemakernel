import pytest
from schemakernel.compliance.redaction import RedactionEngine
from schemakernel.storage.redaction_wrapper import RedactingStorageWrapper
from schemakernel.store import InMemoryStore
from schemakernel.models import SchemaState, PlannerTrace, CompletionOutcome, WorkflowStage

def test_redaction_engine_text():
    engine = RedactionEngine()
    text = "My name is John Doe and my email is john@example.com. Call me at 555-123-4567."
    redacted = engine.redact_text(text)
    
    # Check that PII is gone
    assert "John Doe" not in redacted
    assert "john@example.com" not in redacted
    
    # Basic verification of masks
    assert "<PERSON>" in redacted
    assert "<EMAIL_ADDRESS>" in redacted or "<EMAIL>" in redacted
    assert "<PHONE_NUMBER>" in redacted or "<PHONE>" in redacted

def test_redaction_engine_data():
    engine = RedactionEngine()
    data = {
        "user": "John Doe",
        "contacts": ["jane@example.com", "555-999-9999"],
        "metadata": {"source": "manual", "notes": "Met John at the cafe"}
    }
    redacted = engine.redact_data(data)
    
    assert redacted["user"] == "<PERSON>"
    assert "jane@example.com" not in redacted["contacts"][0]
    assert redacted["metadata"]["notes"] == "Met <PERSON> at the cafe"
    assert redacted["metadata"]["source"] == "manual"

def test_redacting_storage_wrapper_save_state():
    inner_store = InMemoryStore()
    wrapper = RedactingStorageWrapper(inner_store)
    
    state = SchemaState(
        session_id="test-session-1",
        answers={
            "full_name": "Alice Smith",
            "email": "alice@example.com"
        },
        audit_log=[
            {"action": "input", "value": "Alice Smith", "field": "full_name"}
        ],
        stage=WorkflowStage.COLLECTING
    )
    
    wrapper.save_state(state)
    
    # Check that original state is untouched (in-memory)
    assert state.answers["full_name"] == "Alice Smith"
    
    # Check that inner store has redacted data
    stored_state = inner_store.load_state("test-session-1")
    assert stored_state.answers["full_name"] == "<PERSON>"
    # Some versions might use different email tags
    assert "alice@example.com" not in stored_state.answers["email"]
    assert stored_state.audit_log[0]["value"] == "<PERSON>"

def test_redacting_storage_wrapper_save_trace():
    inner_store = InMemoryStore()
    wrapper = RedactingStorageWrapper(inner_store)
    
    trace = PlannerTrace(
        session_id="test-session-2",
        turn=1,
        raw_response={
            "actions": [{"action": "update", "field_key": "name"}],
            "rationale": ["User said his name is John Doe"]
        },
        validated=True
    )
    
    wrapper.save_trace(trace)
    
    stored_traces = inner_store.list_traces("test-session-2")
    assert len(stored_traces) == 1
    assert "John Doe" not in str(stored_traces[0].raw_response)
    assert "<PERSON>" in str(stored_traces[0].raw_response)

def test_redacting_storage_wrapper_save_outcome():
    inner_store = InMemoryStore()
    wrapper = RedactingStorageWrapper(inner_store)
    
    outcome = CompletionOutcome(
        session_id="test-session-3",
        status="complete",
        final_answers={"full_name": "Alice Smith"},
        final_schema={},
        rationale=["Completed"]
    )
    
    wrapper.save_outcome(outcome)
    
    stored_outcome = inner_store.load_outcome("test-session-3")
    assert stored_outcome.final_answers["full_name"] == "<PERSON>"

def test_redaction_non_sensitive_data_preserved():
    engine = RedactionEngine()
    data = {
        "status": "active",
        "count": 42,
        "is_valid": True,
        "description": "This is a regular description with no PII."
    }
    redacted = engine.redact_data(data)
    assert redacted == data
