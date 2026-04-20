import pytest
from tests.vector_utils import load_schema_vectors

def test_load_schema_vectors():
    vectors = load_schema_vectors()
    assert "ValidatorRule" in vectors
    assert "FieldDefinition" in vectors
    assert isinstance(vectors["ValidatorRule"]["valid"], list)
    assert isinstance(vectors["ValidatorRule"]["invalid"], list)
    assert isinstance(vectors["FieldDefinition"]["valid"], list)
    assert isinstance(vectors["FieldDefinition"]["invalid"], list)
