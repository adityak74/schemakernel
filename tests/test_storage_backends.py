import pytest
from sqlalchemy import create_engine
from moto import mock_aws
import boto3

from schemakernel.models import (
    SchemaState,
    PlannerTrace,
    CompletionOutcome,
    WorkflowStage,
    CompletionStatus,
)
from schemakernel.storage.sql import SQLStorageBackend
from schemakernel.storage.dynamodb import DynamoDBStorageBackend
from schemakernel.exceptions import SessionNotFound

@pytest.fixture
def sql_backend():
    engine = create_engine("sqlite:///:memory:")
    return SQLStorageBackend(engine)

@pytest.fixture
def dynamodb_backend():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table_name = "SchemaKernelSessions"
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        yield DynamoDBStorageBackend(table_name, region_name="us-east-1")

def test_sql_backend_roundtrip(sql_backend):
    _run_backend_test(sql_backend)

def test_dynamodb_backend_roundtrip(dynamodb_backend):
    _run_backend_test(dynamodb_backend)

def _run_backend_test(backend):
    session_id = "test-session-123"
    
    # 1. State Roundtrip
    state = SchemaState(
        session_id=session_id,
        fields={},
        field_order=[],
        answers={"name": "Alice", "age": 30},
        stage=WorkflowStage.COLLECTING,
        turn_count=2
    )
    backend.save_state(state)
    loaded_state = backend.load_state(session_id)
    
    assert loaded_state.session_id == state.session_id
    assert loaded_state.answers == state.answers
    assert loaded_state.stage == state.stage
    assert loaded_state.turn_count == state.turn_count
    # Datetime might be stringified/parsed, but they should represent the same time
    assert loaded_state.created_at.isoformat() == state.created_at.isoformat()

    # 2. Trace Roundtrip
    trace1 = PlannerTrace(
        session_id=session_id,
        turn=1,
        raw_response={"foo": "bar"},
        validated=True
    )
    trace2 = PlannerTrace(
        session_id=session_id,
        turn=2,
        raw_response={"error": "invalid"},
        validated=False,
        rejection_reason="Schema violation"
    )
    backend.save_trace(trace1)
    backend.save_trace(trace2)
    
    traces = backend.list_traces(session_id)
    assert len(traces) == 2
    assert traces[0].turn == 1
    assert traces[0].raw_response == {"foo": "bar"}
    assert traces[1].turn == 2
    assert traces[1].validated is False
    assert traces[1].rejection_reason == "Schema violation"

    # 3. Outcome Roundtrip
    outcome = CompletionOutcome(
        session_id=session_id,
        status=CompletionStatus.COMPLETE,
        final_answers={"name": "Alice", "age": 30},
        final_schema={},
        rationale=["All fields collected"]
    )
    backend.save_outcome(outcome)
    loaded_outcome = backend.load_outcome(session_id)
    
    assert loaded_outcome.session_id == session_id
    assert loaded_outcome.status == CompletionStatus.COMPLETE
    assert loaded_outcome.final_answers == {"name": "Alice", "age": 30}
    assert loaded_outcome.rationale == ["All fields collected"]

    # 4. Deletion
    backend.delete_state(session_id)
    
    with pytest.raises(SessionNotFound):
        backend.load_state(session_id)
    
    assert len(backend.list_traces(session_id)) == 0
    
    with pytest.raises(SessionNotFound):
        backend.load_outcome(session_id)

def test_sql_backend_missing_session(sql_backend):
    with pytest.raises(SessionNotFound):
        sql_backend.load_state("non-existent")

def test_dynamodb_backend_missing_session(dynamodb_backend):
    with pytest.raises(SessionNotFound):
        dynamodb_backend.load_state("non-existent")
