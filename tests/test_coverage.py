from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from schemakernel.models import (
    FieldDefinition,
    FieldType,
    ValidatorRule,
    ValidatorType,
)
from schemakernel.policy import (
    PolicyConfig,
    CompletionCriteria,
    ExceptionRule,
)
from schemakernel.validation import ValidationEngine, FieldValidationError
from schemakernel.workflow import WorkflowStateMachine, create_workflow
from schemakernel.store import InMemoryStore

def test_validation_engine_coverage():
    policy = PolicyConfig()
    engine = ValidationEngine(policy)
    
    # Line 211: raise_on_failure in validate_answer
    fd = FieldDefinition(key="f", type=FieldType.INTEGER, label="L")
    with pytest.raises(FieldValidationError):
        engine.validate_answer(fd, "abc", raise_on_failure=True)
        
    # Line 233: FieldType.NUMBER coercion
    fd_num = FieldDefinition(key="n", type=FieldType.NUMBER, label="L")
    val, err = engine._coerce(fd_num, "1.23")
    assert val == 1.23
    assert err is None
    
    # Line 236: Boolean coercion with bool value
    fd_bool = FieldDefinition(key="b", type=FieldType.BOOLEAN, label="L")
    val, err = engine._coerce(fd_bool, True)
    assert val is True
    assert err is None
    
    # Line 241: Boolean coercion with false value
    val, err = engine._coerce(fd_bool, "no")
    assert val is False
    assert err is None
    
    # Coercion failure (Line 249-250)
    val, err = engine._coerce(fd_num, "not-a-number")
    assert err is not None

    # Line 272-273: ValidatorType.MIN except block
    rule_min = ValidatorRule(type=ValidatorType.MIN, value="not-a-number")
    err = engine._check_rule(fd_num, rule_min, 10)
    assert "Cannot compare value" in err.reason

    # Line 280-281: ValidatorType.MAX except block
    rule_max = ValidatorRule(type=ValidatorType.MAX, value="not-a-number")
    err = engine._check_rule(fd_num, rule_max, 10)
    assert "Cannot compare value" in err.reason

    # Line 315-320: NON_NEGATIVE
    rule_nn = ValidatorRule(type=ValidatorType.NON_NEGATIVE)
    assert engine._check_rule(fd_num, rule_nn, 5) is None
    assert engine._check_rule(fd_num, rule_nn, -1) is not None
    assert engine._check_rule(fd_num, rule_nn, "not-a-number") is not None

    # Line 330-342: DATE_AFTER / DATE_BEFORE except block
    fd_date = FieldDefinition(key="d", type=FieldType.DATE, label="L")
    rule_after = ValidatorRule(type=ValidatorType.DATE_AFTER, value="invalid-date")
    err = engine._check_rule(fd_date, rule_after, "2023-01-01")
    assert "Cannot compare date" in err.reason

    rule_before = ValidatorRule(type=ValidatorType.DATE_BEFORE, value="2023-01-01")
    assert engine._check_rule(fd_date, rule_before, "2022-01-01") is None
    assert engine._check_rule(fd_date, rule_before, "2024-01-01") is not None
    
    rule_before_invalid = ValidatorRule(type=ValidatorType.DATE_BEFORE, value="invalid-date")
    err = engine._check_rule(fd_date, rule_before_invalid, "2023-01-01")
    assert "Cannot compare date" in err.reason

def test_workflow_state_machine_coverage():
    policy = PolicyConfig(
        glossary={"T1": "D1"},
        prohibited_topics=["topic1"],
        exception_rules=[ExceptionRule(name="R1", description="D1")],
        completion_criteria=CompletionCriteria(
            required_fields_answered=["f1"],
            minimum_answered_count=5,
            custom_description="Done when happy"
        )
    )
    store = InMemoryStore()
    mock_planner = MagicMock()
    validator = ValidationEngine(policy)
    wf = WorkflowStateMachine(policy, store, mock_planner, validator)
    
    state = wf.start_session()
    prompt = wf._build_system_prompt(state)
    assert "Glossary" in prompt
    assert "T1: D1" in prompt
    assert "Prohibited Topics" in prompt
    assert "topic1" in prompt
    assert "Exception Rules" in prompt
    assert "R1" in prompt
    assert "Completion Criteria" in prompt
    assert "Required fields answered: ['f1']" in prompt
    assert "Minimum answered count: 5" in prompt
    assert "Done when happy" in prompt
    
    # Line 240: fd is None in schema loop
    state.field_order.append("ghost")
    prompt = wf._build_system_prompt(state)
    assert "ghost" not in prompt
    
    # Line 363: _eval_single return False
    from schemakernel.models import Condition, ConditionOperator
    cond = Condition.model_construct(field_key="x", operator="unknown", value=1)
    assert wf._eval_single(cond, {"x": 1}) is False
    
    # Line 367-370: create_workflow
    with MagicMock() as mock_pc:
        # We need to patch PlannerClient to avoid real imports or side effects if any
        # but create_workflow is simple enough.
        wf2 = create_workflow(policy)
        assert isinstance(wf2, WorkflowStateMachine)

def test_policy_config_coverage():
    fd = FieldDefinition(key="f", type=FieldType.TEXT, label="L")
    with pytest.raises(ValueError, match="baseline_questions contains duplicate field keys"):
        PolicyConfig(baseline_questions=[fd, fd])
