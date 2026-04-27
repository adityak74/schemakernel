import json
from schemakernel.models import (
    FieldDefinition, FieldType, ValidatorRule, ValidatorType,
    ActionType, PlannerAction, PlannerResponse, CompletionStatus,
    SchemaState, WorkflowStage, ConditionalLogic, Condition, ConditionOperator
)

def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj

# ------------------------------------------------------------------
# Validation Vectors
# ------------------------------------------------------------------

validation_cases = [
    # Required
    {
        "name": "required_passes",
        "field": FieldDefinition(key="f", type=FieldType.TEXT, label="L", validators=[ValidatorRule(type=ValidatorType.REQUIRED)]),
        "answer": "hello",
        "expected_valid": True
    },
    {
        "name": "required_fails_empty",
        "field": FieldDefinition(key="f", type=FieldType.TEXT, label="L", validators=[ValidatorRule(type=ValidatorType.REQUIRED)]),
        "answer": "",
        "expected_valid": False
    },
    {
        "name": "required_fails_none",
        "field": FieldDefinition(key="f", type=FieldType.TEXT, label="L", validators=[ValidatorRule(type=ValidatorType.REQUIRED)]),
        "answer": None,
        "expected_valid": False
    },
    # Min/Max
    {
        "name": "min_passes",
        "field": FieldDefinition(key="n", type=FieldType.INTEGER, label="N", validators=[ValidatorRule(type=ValidatorType.MIN, value=0)]),
        "answer": 5,
        "expected_valid": True
    },
    {
        "name": "min_fails",
        "field": FieldDefinition(key="n", type=FieldType.INTEGER, label="N", validators=[ValidatorRule(type=ValidatorType.MIN, value=0)]),
        "answer": -1,
        "expected_valid": False
    },
    # Coercion
    {
        "name": "integer_coercion",
        "field": FieldDefinition(key="n", type=FieldType.INTEGER, label="N"),
        "answer": "42",
        "expected_valid": True
    },
    {
        "name": "boolean_coercion_yes",
        "field": FieldDefinition(key="b", type=FieldType.BOOLEAN, label="B"),
        "answer": "yes",
        "expected_valid": True
    },
    # Date
    {
        "name": "date_after_passes",
        "field": FieldDefinition(key="d", type=FieldType.DATE, label="D", validators=[ValidatorRule(type=ValidatorType.DATE_AFTER, value="2000-01-01")]),
        "answer": "2024-06-15",
        "expected_valid": True
    },
    {
        "name": "date_after_fails",
        "field": FieldDefinition(key="d", type=FieldType.DATE, label="D", validators=[ValidatorRule(type=ValidatorType.DATE_AFTER, value="2030-01-01")]),
        "answer": "2024-06-15",
        "expected_valid": False
    },
    # Enum
    {
        "name": "enum_member_passes",
        "field": FieldDefinition(
            key="s", type=FieldType.SELECT, label="S", options=["a", "b"],
            validators=[ValidatorRule(type=ValidatorType.ENUM_MEMBER)]
        ),
        "answer": "a",
        "expected_valid": True
    },
    {
        "name": "enum_member_fails",
        "field": FieldDefinition(
            key="s", type=FieldType.SELECT, label="S", options=["a", "b"],
            validators=[ValidatorRule(type=ValidatorType.ENUM_MEMBER)]
        ),
        "answer": "c",
        "expected_valid": False
    }
]

validation_vectors = []
for case in validation_cases:
    validation_vectors.append({
        "name": case["name"],
        "field": to_dict(case["field"]),
        "answer": case["answer"],
        "expected_valid": case["expected_valid"]
    })

with open("vectors/validation_vectors.json", "w") as f:
    json.dump(validation_vectors, f, indent=2)

# ------------------------------------------------------------------
# Workflow Vectors
# ------------------------------------------------------------------

workflow_cases = [
    {
        "name": "add_field",
        "initial_state": SchemaState(session_id="test", stage=WorkflowStage.COLLECTING),
        "response": PlannerResponse(
            actions=[PlannerAction(action=ActionType.ADD, field_key="f")],
            fields=[FieldDefinition(key="f", type=FieldType.TEXT, label="F")],
            rationale=["adding f"],
            completion_status=CompletionStatus.IN_PROGRESS
        ),
        "expected_fields": ["f"],
        "expected_stage": "collecting"
    },
    {
        "name": "complete_workflow",
        "initial_state": SchemaState(session_id="test", stage=WorkflowStage.COLLECTING),
        "response": PlannerResponse(
            actions=[PlannerAction(action=ActionType.COMPLETE)],
            rationale=["done"],
            completion_status=CompletionStatus.COMPLETE
        ),
        "expected_stage": "complete"
    },
    {
        "name": "reorder_fields",
        "initial_state": SchemaState(
            session_id="test",
            fields={
                "f1": FieldDefinition(key="f1", type=FieldType.TEXT, label="F1"),
                "f2": FieldDefinition(key="f2", type=FieldType.TEXT, label="F2")
            },
            field_order=["f1", "f2"]
        ),
        "response": PlannerResponse(
            actions=[PlannerAction(action=ActionType.REORDER, field_key="f2", position=0)],
            rationale=["reordering"],
            completion_status=CompletionStatus.IN_PROGRESS
        ),
        "expected_order": ["f2", "f1"]
    }
]

workflow_vectors = []
for case in workflow_cases:
    workflow_vectors.append({
        "name": case["name"],
        "initial_state": to_dict(case["initial_state"]),
        "response": to_dict(case["response"]),
        "expected_fields": case.get("expected_fields"),
        "expected_stage": case.get("expected_stage"),
        "expected_order": case.get("expected_order")
    })

with open("vectors/workflow_vectors.json", "w") as f:
    json.dump(workflow_vectors, f, indent=2)

# ------------------------------------------------------------------
# Condition Vectors
# ------------------------------------------------------------------

condition_cases = [
    {
        "name": "eq_true",
        "logic": ConditionalLogic(conditions=[Condition(field_key="x", operator=ConditionOperator.EQ, value="yes")]),
        "answers": {"x": "yes"},
        "expected": True
    },
    {
        "name": "eq_false",
        "logic": ConditionalLogic(conditions=[Condition(field_key="x", operator=ConditionOperator.EQ, value="yes")]),
        "answers": {"x": "no"},
        "expected": False
    },
    {
        "name": "gt_true",
        "logic": ConditionalLogic(conditions=[Condition(field_key="age", operator=ConditionOperator.GT, value=18)]),
        "answers": {"age": 21},
        "expected": True
    },
    {
        "name": "in_true",
        "logic": ConditionalLogic(conditions=[Condition(field_key="color", operator=ConditionOperator.IN, value=["red", "blue"])]),
        "answers": {"color": "red"},
        "expected": True
    },
    {
        "name": "and_logic",
        "logic": ConditionalLogic(combinator="and", conditions=[
            Condition(field_key="a", operator=ConditionOperator.EQ, value=1),
            Condition(field_key="b", operator=ConditionOperator.EQ, value=2)
        ]),
        "answers": {"a": 1, "b": 2},
        "expected": True
    },
    {
        "name": "or_logic",
        "logic": ConditionalLogic(combinator="or", conditions=[
            Condition(field_key="a", operator=ConditionOperator.EQ, value=1),
            Condition(field_key="b", operator=ConditionOperator.EQ, value=2)
        ]),
        "answers": {"a": 1, "b": 3},
        "expected": True
    }
]

condition_vectors = []
for case in condition_cases:
    condition_vectors.append({
        "name": case["name"],
        "logic": to_dict(case["logic"]),
        "answers": case["answers"],
        "expected": case["expected"]
    })

with open("vectors/condition_vectors.json", "w") as f:
    json.dump(condition_vectors, f, indent=2)
