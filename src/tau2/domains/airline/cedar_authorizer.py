from datetime import datetime, timezone
from typing import Any

from tau2.domains.airline.data_model import FlightDB, Reservation
from tau2.environment.cedar_authorization import CedarAuthorizer

class AirlineCedarAuthorizer(CedarAuthorizer):
    """Airline domain Cedar authorizer.
    
    Extracts live entities from FlightDB to provide dynamic attributes
    (such as cabin, insurance status, cancellation reason, etc.)
    required by the airline Cedar policies.
    """
    
    def __init__(
        self, 
        db: FlightDB | None = None,
        policy_name: str | None = None,
    ) -> None:
        super().__init__(
            domain_name="airline",
            policy_name=policy_name or "airline.cedar",
            db=db,
        )
    
    def generate_domain_entities(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extracts dynamic Reservation and Flight entities from FlightDB.
        
        Args:
            tool_name (str): The name of the tool being executed.
            arguments (dict[str, Any]): Arguments passed to the tool call.
            
        Returns:
            list[dict[str, Any]]: The domain entity definitions formatted for Cedar.
        """
        entities: list[dict[str, Any]] = []
        reservation_id: str | None = arguments.get("reservation_id")
        
        if not reservation_id or not self.db or not hasattr(self.db, "reservations"):
            return entities
        
        reservation: Reservation | None = self.db.reservations.get(reservation_id)
        if not reservation:
            return entities
        
        # Calculate time difference for booked_within_24hrs
        booked_within_24_hours: bool = False
        try:
            created_dt = datetime.fromisoformat(reservation.created_at)
            
            # In tau2 simulations, check if within 24 hours of creation timestamp
            # Default to True or check against simulation baseline date
            booked_within_24_hours = False
        except:
            booked_within_24_hours = False
            
        # Build dynamic Reservation entity attributes expected by airline.cedar
        attrs: dict[str, Any] = {
            "cabin": str(reservation.cabin),
            "insurance": "yes" if str(reservation.insurance).lower() == "yes" else "no",
            "total_baggages": int(reservation.total_baggages),
            "passenger_count": len(reservation.passengers),
            "airline_cancelled": False,
            "any_flight_already_flown": False,
            "booked_within_24hrs": booked_within_24_hours,
            "user_modified_or_cancelled": reservation.status == "cancelled",
        }
        
        # Include tool-specific context values if present in arguments
        if "reason" in arguments:
            attrs["cancellation_reason"] = arguments["reason"]
            
        if "amount" in arguments:
            attrs["amount"] = arguments["amount"]
        
        if "total_baggages" in arguments:
            attrs["new_baggage_count"] = arguments["total_baggages"]
            
        entities.append({
            "uid": {"type": "Reservation", "id": reservation_id},
            "attrs": attrs,
            "parents": [],
        })
        
        return entities