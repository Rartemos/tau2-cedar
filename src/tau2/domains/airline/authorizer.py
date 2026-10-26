from datetime import datetime
from pathlib import Path
from typing import Any

from tau2.domains.airline.data_model import FlightDB, Reservation, Flight, FlightDateStatus
from tau2.environment.authorizer import CedarAuthorizer

class AirlineCedarAuthorizer(CedarAuthorizer):
    """Airline domain Cedar authorizer.
    
    Extracts live entities from FlightDB to provide attributes
    (such as cabin, insurance status, cancellation reason, etc.)
    required by airline Cedar policies.
    """
    
    def __init__(
        self,
        db: FlightDB | None = None, 
        policy_path: str | Path | None = None,
        schema_path: str | Path | None = None,
        **kwargs,
    ) -> None:
        """Initialize the airline authorizer.
    
        Args:
            db: FlightDB instance for live entity extraction.
            policy_path: The Cedar policy file path. Defaults to ``airline.cedar``.
            schema_path: The Cedar schema file path, if provided.
            **kwargs: Additional keyword arguments forwarded to CedarAuthorizer.
        """
        super().__init__(
            domain_name="airline",
            policy_path=policy_path,
            schema_path=schema_path,
            db=db,
            **kwargs,
        )
    
    def build_entities(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract Reservation and Flight entities from FlightDB.
        
        Args:
            tool_name: The name of the tool call.
            arguments: The raw tool parameters.
            
        Returns:
            The entity slice formatted for Cedar evaluation, including base entities.
        """
        entities: list[dict[str, Any]] = [
            entity for entity in super().build_entities(tool_name, arguments)
            if entity["uid"]["type"] != "User"
        ]
        
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
            
        # Resolve user membership for User entity
        user_membership = "regular"
        if hasattr(self.db, "users") and reservation.user_id in self.db.users:
            user_obj = self.db.users[reservation.user_id]
            user_membership = str(getattr(user_obj, "membership", "regular"))
            
        # Build dynamic Reservation entity with all attributes required by airline.cedarschema
        attrs: dict[str, Any] = {
            "cabin": str(reservation.cabin),
            "insurance": "yes" if str(reservation.insurance).lower() == "yes" else "no",
            "total_baggages": int(reservation.total_baggages),
            "passenger_count": len(reservation.passengers),
            "airline_cancelled": airline_cancelled,
            "any_flight_already_flown": any_flight_already_flown,
            "booked_within_24hrs": booked_within_24_hours,
            "user_modified_or_cancelled": reservation.status == "cancelled",
            # Contextual attributes with arguments / defaults:
            "cancellation_reason": str(arguments.get("reason", "")),
            "amount": int(arguments.get("amount", 0)),
            "new_baggage_count": int(arguments.get("total_baggages", reservation.total_baggages)),
            "origin_changed": bool(arguments.get("origin_changed", False)),
            "destination_changed": bool(arguments.get("destination_changed", False)),
            "payment_not_in_profile": bool(arguments.get("payment_not_in_profile", False)),
            "cabin_mismatch": bool(arguments.get("cabin_mismatch", False)),
            "certificate_count": int(arguments.get("certificate_count", 0)),
            "credit_card_count": int(arguments.get("credit_card_count", 1)),
            "gift_card_count": int(arguments.get("gift_card_count", 0)),
        }
        
        entities.append({
            "uid": {"type": "Reservation", "id": reservation_id},
            "attrs": attrs,
            "parents": [],
        })
        entities.append({
            "uid": {"type": "User", "id": str(reservation.user_id)},
            "attrs": {"membership": user_membership},
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
            tool_name: The name of the tool call.
            arguments: The sanitized tool parameters.
        
        Returns:
            The formatted Cedar Resource ID string.
        """
        if tool_name == "transfer_to_human_agents":
            return 'Reservation::"new_context"'
        if tool_name == "search_direct_flight":
            return 'Flight::"new_context"'
        return super()._determine_resource(tool_name, arguments)
        