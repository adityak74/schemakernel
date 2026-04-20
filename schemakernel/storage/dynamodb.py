from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from schemakernel.models import CompletionOutcome, PlannerTrace, SchemaState
from schemakernel.store import StorageBackend
from schemakernel.exceptions import SessionNotFound

def _to_dynamo(data: Any) -> Any:
    """Recursively convert float to Decimal for DynamoDB."""
    if isinstance(data, list):
        return [_to_dynamo(v) for v in data]
    if isinstance(data, dict):
        return {k: _to_dynamo(v) for k, v in data.items()}
    if isinstance(data, float):
        return Decimal(str(data))
    return data

def _from_dynamo(data: Any) -> Any:
    """Recursively convert Decimal to float/int for Pydantic."""
    if isinstance(data, list):
        return [_from_dynamo(v) for v in data]
    if isinstance(data, dict):
        return {k: _from_dynamo(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        if data % 1 == 0:
            return int(data)
        return float(data)
    return data

class DynamoDBStorageBackend(StorageBackend):
    def __init__(self, table_name: str, region_name: str = None, endpoint_url: str = None):
        self.dynamodb = boto3.resource(
            "dynamodb", region_name=region_name, endpoint_url=endpoint_url
        )
        self.table = self.dynamodb.Table(table_name)

    def save_state(self, state: SchemaState) -> None:
        item = {
            "pk": f"SESSION#{state.session_id}",
            "sk": "STATE",
            "data": _to_dynamo(state.model_dump(mode="json")),
            "session_id": state.session_id,
            "type": "state",
        }
        self.table.put_item(Item=item)

    def load_state(self, session_id: str) -> SchemaState:
        response = self.table.get_item(Key={"pk": f"SESSION#{session_id}", "sk": "STATE"})
        if "Item" not in response:
            raise SessionNotFound(f"Session '{session_id}' not found")
        return SchemaState.model_validate(_from_dynamo(response["Item"]["data"]))

    def delete_state(self, session_id: str) -> None:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(f"SESSION#{session_id}")
        )
        for item in response.get("Items", []):
            self.table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    def save_trace(self, trace: PlannerTrace) -> None:
        # Use turn for sorting traces
        item = {
            "pk": f"SESSION#{trace.session_id}",
            "sk": f"TRACE#{trace.turn:04d}",
            "data": _to_dynamo(trace.model_dump(mode="json")),
            "session_id": trace.session_id,
            "type": "trace",
        }
        self.table.put_item(Item=item)

    def list_traces(self, session_id: str) -> list[PlannerTrace]:
        response = self.table.query(
            KeyConditionExpression=(
                Key("pk").eq(f"SESSION#{session_id}") & Key("sk").begins_with("TRACE#")
            )
        )
        return [
            PlannerTrace.model_validate(_from_dynamo(item["data"]))
            for item in response.get("Items", [])
        ]

    def save_outcome(self, outcome: CompletionOutcome) -> None:
        item = {
            "pk": f"SESSION#{outcome.session_id}",
            "sk": "OUTCOME",
            "data": _to_dynamo(outcome.model_dump(mode="json")),
            "session_id": outcome.session_id,
            "type": "outcome",
        }
        self.table.put_item(Item=item)

    def load_outcome(self, session_id: str) -> CompletionOutcome:
        response = self.table.get_item(Key={"pk": f"SESSION#{session_id}", "sk": "OUTCOME"})
        if "Item" not in response:
            raise SessionNotFound(f"No outcome for session '{session_id}'")
        return CompletionOutcome.model_validate(_from_dynamo(response["Item"]["data"]))
