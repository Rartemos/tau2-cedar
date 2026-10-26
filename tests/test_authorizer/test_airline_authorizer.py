from datetime import datetime
import pytest
from tau2.domains.airline.environment import get_environment
from tau2.environment.authorizer import CedarError
from tau2.environment.environment import Environment

@pytest.fixture(scope="module")
def env() -> Environment:
    """Load airline environment with default FlightDB and AirlineCedarAuthorizer."""
    return get_environment()

@pytest.fixture(scope="module")
def authorizer(env: Environment):
    """Load the authorizer for the airline domain."""
    return env.cedar_authorizer

@pytest.fixture(scope="module")
def non_refundable_reservation_id(env: Environment) -> str:
    """
    Find a reservation that CANNOT be cancelled:
    - economy/basic_economy
    - no insurance
    - booked MORE than 24 hours before simulation time (2024-05-15T15:00:00)
    """
    current_sim_time = datetime.fromisoformat("2024-05-15T15:00:00")
    for res_id, res in env.tools.db.reservations.items():
        created_at = datetime.fromisoformat(res.created_at)
        booked_over_24h = (current_sim_time - created_at).total_seconds() > 24 * 3600
        if res.cabin in ("economy", "basic_economy") and res.insurance == "no" and booked_over_24h:
            return res_id
    
    return "EHGLP3" # Fallback to non-refundable reservation (task 0)

def test_airline_entity_extraction(authorizer, non_refundable_reservation_id):
    """Verify AirlineCedarAuthorizer properly extracts all entities from FlightDB."""
    entities = authorizer.build_entities(
        "cancel_reservation",
        {"reservation_id": non_refundable_reservation_id, "reason": "vacation"},
    )
    
    # Verify entity extraction
    res_entity = next(e for e in entities if e["uid"]["type"] == "Reservation")
    assert res_entity["attrs"]["cabin"] in ("economy", "basic_economy")
    assert res_entity["attrs"]["insurance"] == "no"
    assert res_entity["attrs"]["booked_within_24hrs"] is False
    assert res_entity["attrs"]["cancellation_reason"] == "vacation"

def test_permit_read(authorizer, non_refundable_reservation_id):
    """Safe read requests should be permitted."""
    result = authorizer.authorize_tool_call(
        tool_name="get_reservation_details",
        requestor="assistant",
        arguments={"reservation_id": non_refundable_reservation_id},
    )
    assert result is not None
    assert result["cedar_overhead_ms"] > 0
    assert len(result.get("cedar_eval_errors", [])) == 0
    
def test_deny_uninsured_cancellation(authorizer, non_refundable_reservation_id):
    """Non-refundable economy cancellation without insurance must raise CedarError."""
    with pytest.raises(CedarError) as e:
        authorizer.authorize_tool_call(
            tool_name="cancel_reservation",
            requestor="assistant",
            arguments={"reservation_id": non_refundable_reservation_id, "reason": "vacation"},
        )
    error = e.value
    assert error.tool_name == "cancel_reservation"
    assert error.requestor == "assistant"
    assert error.cedar_overhead_ms is not None
    
def test_environment_catch_deny(env: Environment, non_refundable_reservation_id):
    """When Cedar blocks a tool, Environment should catch it, return a deny dict and log."""
    previous_denials = env.cedar_logger.get_summary()["decisions"]["deny"]
    
    # Read tool denial
    result = env.use_tool(
        tool_name="cancel_reservation",
        requestor="assistant",
        reservation_id=non_refundable_reservation_id,
        reason="vacation",
    )
    assert result["decision"] == "deny"
    assert "policy_feedback" in result
    
    # Ensure that the denial was recorded
    current_denials = env.cedar_logger.get_summary()["decisions"]["deny"]
    assert current_denials == previous_denials + 1