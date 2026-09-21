from datetime import datetime
from typing import Any

from tau2.domains.airline.data_model import FlightDB, Reservation, Flight, FlightDateStatus
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
    
    def _generate_domain_entities(
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
        
        # Calculate booked_within_24hrs relative to current simulation time
        current_sim_time: datetime = datetime.fromisoformat("2024-05-15T15:00:00")
        booked_within_24_hours: bool = False
        try:
            created_at: datetime = datetime.fromisoformat(reservation.created_at)
            diff_seconds: float = (current_sim_time - created_at).total_seconds()
            booked_within_24_hours = 0 <= diff_seconds <= 24 * 3600
        except Exception:
            booked_within_24_hours = False
            
        # Check if any flight was already flown or cancelled by the airline
        airline_cancelled: bool = False
        any_flight_already_flown: bool = False
        if hasattr(self.db, "flights"):
            for f in reservation.flights:
                flight_obj: Flight | None = self.db.flights.get(f.flight_number)
                if flight_obj and f.date in flight_obj.dates:
                    date_status: FlightDateStatus = flight_obj.dates[f.date]
                    status: str | None = getattr(date_status, "status", None)
                    if status == "cancelled":
                        airline_cancelled = True
                    elif status in ("landed", "flying"):
                        any_flight_already_flown = True
            
        # Build dynamic Reservation entity attributes expected by airline.cedar
        attrs: dict[str, Any] = {
            "cabin": str(reservation.cabin),
            "insurance": "yes" if str(reservation.insurance).lower() == "yes" else "no",
            "total_baggages": int(reservation.total_baggages),
            "passenger_count": len(reservation.passengers),
            "airline_cancelled": airline_cancelled,
            "any_flight_already_flown": any_flight_already_flown,
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
    
    def _determine_resource(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Determines the Cedar Resource identifier for the airline domain.
        
        Args:
            tool_name (str): The name of the tool being called.
            arguments (dict[str, Any]): The arguments passed to the tool.
        
        Returns:
            str: The formatted Cedar Resource ID string.
        """
        if tool_name == "transfer_to_human_agents":
            return 'Reservation::"new_context"'
        if tool_name == "search_direct_flight":
            return 'Flight::"new_context"'
        return super()._determine_resource(tool_name, arguments)
        