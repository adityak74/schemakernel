import pytest
from sqlalchemy import create_engine
from schemakernel.policy import PolicyConfig, ExperimentRouter
from schemakernel.storage.versioning import VersionedPolicyStore, PolicyResolver
from schemakernel.models import FieldDefinition, FieldType

@pytest.fixture
def engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture
def store(engine):
    return VersionedPolicyStore(engine)

@pytest.fixture
def policy_config():
    return PolicyConfig(
        baseline_questions=[
            FieldDefinition(key="name", label="Full Name", type=FieldType.TEXT)
        ],
        reasoning_style="concise"
    )

def test_version_saving_and_retrieval(store, policy_config):
    v1_id = store.save_version("test-policy", policy_config, "Initial version")
    assert v1_id is not None
    
    retrieved = store.get_version(v1_id)
    assert retrieved is not None
    assert retrieved.reasoning_style == "concise"
    assert retrieved.baseline_questions[0].key == "name"

    # Save another version
    policy_config.reasoning_style = "verbose"
    v2_id = store.save_version("test-policy", policy_config, "Updated version")
    
    assert v2_id != v1_id
    
    v1_retrieved = store.get_version(v1_id)
    v2_retrieved = store.get_version(v2_id)
    
    assert v1_retrieved is not None
    assert v2_retrieved is not None
    assert v1_retrieved.reasoning_style == "concise"
    assert v2_retrieved.reasoning_style == "verbose"

def test_alias_resolution(store, policy_config):
    v1_id = store.save_version("test-policy", policy_config, "V1")
    store.set_alias("production", "test-policy", v1_id)
    
    resolver = PolicyResolver(store)
    resolved = resolver.resolve("production", is_alias=True)
    assert resolved is not None
    assert resolved.reasoning_style == "concise"

    # Update alias
    policy_config.reasoning_style = "verbose"
    v2_id = store.save_version("test-policy", policy_config, "V2")
    store.set_alias("production", "test-policy", v2_id)
    
    resolved = resolver.resolve("production", is_alias=True)
    assert resolved is not None
    assert resolved.reasoning_style == "verbose"

def test_experiment_router_consistency():
    variants = {"A": 0.5, "B": 0.5}
    router = ExperimentRouter()
    
    session_1 = "session-123"
    variant_1 = router.get_variant(session_1, variants)
    assert variant_1 in ["A", "B"]
    
    # Must be consistent
    for _ in range(10):
        assert router.get_variant(session_1, variants) == variant_1

    session_2 = "session-456"
    variant_2 = router.get_variant(session_2, variants)
    # Could be same or different, but must be consistent for session_2
    for _ in range(10):
        assert router.get_variant(session_2, variants) == variant_2

def test_experiment_router_distribution():
    variants = {"A": 0.2, "B": 0.8}
    router = ExperimentRouter()
    
    counts = {"A": 0, "B": 0}
    for i in range(1000):
        v = router.get_variant(f"user-{i}", variants)
        counts[v] += 1
    
    # Check if roughly 20/80 split (allowing some variance)
    assert 150 < counts["A"] < 250
    assert 750 < counts["B"] < 850

def test_list_versions(store, policy_config):
    store.save_version("policy-a", policy_config, "V1")
    store.save_version("policy-a", policy_config, "V2")
    store.save_version("policy-b", policy_config, "V1")
    
    versions_a = store.list_versions("policy-a")
    assert len(versions_a) == 2
    assert all(v["policy_name"] == "policy-a" for v in versions_a)
    
    versions_b = store.list_versions("policy-b")
    assert len(versions_b) == 1
    assert versions_b[0]["policy_name"] == "policy-b"
