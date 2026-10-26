import pytest
from tau2.domains.retail.environment import get_environment
from tau2.environment.authorizer import CedarError
from tau2.environment.environment import Environment

@pytest.fixture(scope="module")
def env() -> Environment:
    """Load retail environment with default RetailDB and RetailCedarAuthorizer."""
    return get_environment()

@pytest.fixture(scope="module")
def authorizer(env: Environment):
    """Load the authorizer for the retail domain."""
    return env.cedar_authorizer

@pytest.fixture(scope="module")
def sample_pending_order_id(env: Environment) -> str:
    """Find a pending order in the database."""
    for order_id, order in env.tools.db.orders.items():
        if order.status == "pending":
            return order_id
    raise ValueError("No delivered order found in retail database")

def test_retail_entity_extraction(authorizer, sample_pending_order_id):
    """Verify RetailCedarAuthorizer properly extracts Order and User entities from RetailDB."""
    entities = authorizer.build_entities(
        "cancel_pending_order",
        {"order_id": sample_pending_order_id, "reason": "no longer needed"},
    )
    
    # Verify Order entity extraction
    order_entity = next((e for e in entities if e["uid"]["type"] == "Order"), None)
    assert order_entity is not None
    assert order_entity["attrs"]["status"] == "pending"
    assert order_entity["attrs"]["is_pending"] is True
    assert order_entity["attrs"]["is_delivered"] is False
    assert "user_id" in order_entity["attrs"]
    
    # Verify User entity extraction
    user_entity = next((e for e in entities if e["uid"]["type"] == "User"), None)
    assert user_entity is not None
    assert "email" in user_entity["attrs"]
    
def test_permit_read(authorizer, sample_pending_order_id):
    """Safe read requests should be permitted."""
    result = authorizer.authorize_tool_call(
        tool_name="get_order_details",
        requestor="assistant",
        arguments={"order_id": sample_pending_order_id},
    )
    assert result is not None
    assert result["cedar_overhead_ms"] > 0
    assert len(result.get("cedar_eval_errors", [])) == 0
    
def test_environment_tool_call(env: Environment, sample_pending_order_id):
    """Verify environment tool execution and logging."""
    previous_summary = env.cedar_logger.get_summary()
    previous_total = previous_summary["total_tool_calls"]
    
    # Read tool execution
    result = env.use_tool(
        tool_name="get_order_details",
        requestor="assistant",
        order_id=sample_pending_order_id,
    )
    assert result is not None
    
    # Ensure that the call was recorded
    new_summary = env.cedar_logger.get_summary()
    assert new_summary["total_tool_calls"] == previous_total + 1