// -----------------------------------------------------------------------------
// airline_policy.cedar — Full Airline Domain Policy (Corrected)
//
// Purpose: Production Cedar policy for the tau2-bench airline domain.
//          Contains all rules from airline_policy_1.cedar with the following
//          corrections applied:
//
//          1. FIXED: "changeCabin" renamed to "change_cabin" to match the
//             actual tool name registered in AirlineTools.
//          2. ADDED: Permits for 5 missing tools that were implicitly denied:
//             search_onestop_flight, get_flight_status, list_all_airports,
//             calculate, update_reservation_passengers.
// -----------------------------------------------------------------------------


// =============================================================================
// CANCEL RESERVATION
// =============================================================================

// Default: permit cancellation.
permit (principal is Agent, action == Action::"cancel_reservation", resource is Reservation);

// Forbid if any flight in the reservation has already been flown.
forbid (principal is Agent, action == Action::"cancel_reservation", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

// Forbid if none of the valid cancellation conditions are met:
//   - Not booked within 24 hours
//   - Not cancelled by the airline
//   - Not a business cabin
//   - No valid insurance + covered reason (health or weather)
forbid (principal is Agent, action == Action::"cancel_reservation", resource is Reservation)
when {
    resource.booked_within_24hrs == false &&
    resource.airline_cancelled == false &&
    resource.cabin != "business" &&
    !(
        resource.insurance == "yes" &&
        (
            resource.cancellation_reason == "health" ||
            resource.cancellation_reason == "weather"
        )
    )
};


// =============================================================================
// SEND CERTIFICATE (Compensation)
// =============================================================================

// Permit only if the agent has confirmed the facts AND the user qualifies
// (silver/gold member, has insurance, or flies business).
permit (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    context.confirmed == true &&
    (
        context.membership == "silver" ||
        context.membership == "gold" ||
        context.insurance == "yes" ||
        context.cabin == "business"
    )
};

// Forbid for regular members without insurance flying economy/basic economy.
forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    context.membership == "regular" &&
    context.insurance == "no" &&
    (
        context.cabin == "economy" ||
        context.cabin == "basic_economy"
    )
};

// Forbid if the user has not modified or cancelled a reservation first.
forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    resource.user_modified_or_cancelled == false
};

// Forbid if the certificate amount doesn't match the valid formula
// ($50 or $100 per passenger).
forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    resource.amount != resource.passenger_count * 50 &&
    resource.amount != resource.passenger_count * 100
};


// =============================================================================
// UPDATE RESERVATION FLIGHTS (Modify Flights)
// =============================================================================

// Default: permit flight modifications.
permit (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation);

// Forbid if the reservation is basic economy.
forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.cabin == "basic_economy"
};

// Forbid if the origin has changed.
forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.origin_changed == true
};

// Forbid if the destination has changed.
forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.destination_changed == true
};

// Forbid if the payment method is not in the user's profile.
forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.payment_not_in_profile == true
};


// =============================================================================
// UPDATE RESERVATION BAGGAGES
// =============================================================================

// Default: permit baggage updates.
permit (principal is Agent, action == Action::"update_reservation_baggages", resource is Reservation);

// Forbid removing bags (new count must not be less than current total).
forbid (principal is Agent, action == Action::"update_reservation_baggages", resource is Reservation)
when {
    resource.new_baggage_count < resource.total_baggages
};


// =============================================================================
// CHANGE CABIN
// FIX: Renamed from "changeCabin" to "change_cabin" to match the actual
//      tool name in the tau2-bench AirlineTools registry.
// =============================================================================

// Default: permit cabin changes.
permit (principal is Agent, action == Action::"change_cabin", resource is Reservation);

// Forbid if any flight has already been flown.
forbid (principal is Agent, action == Action::"change_cabin", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

// Forbid if there is a cabin class mismatch across flights.
forbid (principal is Agent, action == Action::"change_cabin", resource is Reservation)
when {
    resource.cabin_mismatch == true
};


// =============================================================================
// BOOK RESERVATION
// =============================================================================

// Default: permit new bookings.
permit (principal is Agent, action == Action::"book_reservation", resource is Reservation);

// Forbid if more than 5 passengers.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.passenger_count > 5
};

// Forbid if there is a cabin class mismatch.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.cabin_mismatch == true
};

// Forbid if the payment method is not in the user's profile.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.payment_not_in_profile == true
};

// Forbid more than 1 travel certificate per reservation.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.certificate_count > 1
};

// Forbid more than 1 credit card per reservation.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.credit_card_count > 1
};

// Forbid more than 3 gift cards per reservation.
forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.gift_card_count > 3
};


// =============================================================================
// READ-ONLY TOOLS (Always Permitted)
// =============================================================================

// Lookup user profile information.
permit (principal is Agent, action == Action::"get_user_details", resource is User);

// Lookup reservation details.
permit (principal is Agent, action == Action::"get_reservation_details", resource is Reservation);

// Search for direct flights.
permit (principal is Agent, action == Action::"search_direct_flight", resource is Flight);

// ADDED: Search for one-stop (connecting) flights.
permit (principal is Agent, action == Action::"search_onestop_flight", resource is Flight);

// ADDED: Check the status of a specific flight.
permit (principal is Agent, action == Action::"get_flight_status", resource is Status);

// ADDED: List all available airports.
permit (principal is Agent, action == Action::"list_all_airports", resource is Airports);

// ADDED: Perform arithmetic calculations (e.g., price differences).
permit (principal is Agent, action == Action::"calculate", resource is System);


// =============================================================================
// WRITE TOOLS (Additional)
// =============================================================================

// ADDED: Update passenger details on an existing reservation.
permit (principal is Agent, action == Action::"update_reservation_passengers", resource is Reservation);


// =============================================================================
// TRANSFER TO HUMAN AGENTS
// =============================================================================

// Permit transfer if the agent cannot handle the request.
permit (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    principal.cannot_handle == true
};

// Permit transfer if any flight has already been flown.
permit (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

// Forbid transfer if the agent can handle it and no flights have been flown.
forbid (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    principal.cannot_handle == false &&
    resource.any_flight_already_flown == false
};
