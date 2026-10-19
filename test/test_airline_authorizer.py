import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tau2.domains.airline.environment import get_environment
from tau2.environment.authorizer import CedarError

def main():
    print("=== 1. Initializing Airline Environment ===")
    env = get_environment()
    auth = env.cedar_authorizer
    print("Authorizer class:", type(auth).__name__)
    
    # Pick an economy reservation without insurance
    econ_res = [r for r in env.tools.db.reservations.values() if r.cabin == "economy" and r.insurance == "no"][0] # pyright: ignore[reportOptionalMemberAccess]
    print(f"\nTarget Economy Reservation ID: {econ_res.reservation_id}")
    print(f"Cabin: {econ_res.cabin}, Insurance: {econ_res.insurance}")
    
    # Check generated dynamic entities
    print("\n=== 2. Inspecting Dynamic Entity Extraction ===")
    entities = auth.build_entities("cancel_reservation", {"reservation_id": econ_res.reservation_id, "reason": "vacation"})
    for e in entities:
        print(f"Entity: {e['uid']} -> Attrs: {e.get('attrs')}")
        
    # Test 1: Permitted tool call (get_reservation_details)
    print("\n=== 3. Testing Permitted Tool Call ===")
    allow_res = auth.authorize_tool_call("get_reservation_details", "assistant", {"reservation_id": econ_res.reservation_id})
    print("SUCCESS: get_reservation_details was ALLOWED")
    print("Satisfied policy reasons:", allow_res["cedar_policy_ids"])
    print(f"Latency: {allow_res['cedar_overhead_ms']:.2f} ms")

    # Test 2: Forbidden tool call (cancel non-refundable economy reservation without valid reason)
    print("\n=== 4. Testing Forbidden Tool Call (Denial) ===")
    try:
        auth.authorize_tool_call("cancel_reservation", "assistant", {"reservation_id": econ_res.reservation_id, "reason": "vacation"})
        print("ERROR: Should have been denied")
    except CedarError as e:
        print("SUCCESS: cancel_reservation was correctly DENIED")
        print("Denial Reason:", e.reason)
        print("Triggered Forbid Policy IDs:", e.cedar_policy_ids)
        print(f"Latency: {e.cedar_overhead_ms:.2f} ms")

    print("\n>>> ALL OFFLINE TESTS PASSED <<<")

if __name__ == "__main__":
    main()
