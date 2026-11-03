permit (principal is Agent, action == Action::"cancel_reservation", resource is Reservation);

forbid (principal is Agent, action == Action::"cancel_reservation", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

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

forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    context.membership == "regular" &&
    context.insurance == "no" &&
    (
        context.cabin == "economy" ||
        context.cabin == "basic_economy"
    )
};

forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    resource.user_modified_or_cancelled == false
};

forbid (principal is Agent, action == Action::"send_certificate", resource is Reservation)
when {
    resource.amount != resource.passenger_count * 50 &&
    resource.amount != resource.passenger_count * 100
};

permit (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation);

forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.cabin == "basic_economy"
};

forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.origin_changed == true
};

forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.destination_changed == true
};

forbid (principal is Agent, action == Action::"update_reservation_flights", resource is Reservation)
when {
    resource.payment_not_in_profile == true
};

permit (principal is Agent, action == Action::"update_reservation_baggages", resource is Reservation);

forbid (principal is Agent, action == Action::"update_reservation_baggages", resource is Reservation)
when {
    resource.new_baggage_count < resource.total_baggages
};

permit (principal is Agent, action == Action::"change_cabin", resource is Reservation);

forbid (principal is Agent, action == Action::"change_cabin", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

forbid (principal is Agent, action == Action::"change_cabin", resource is Reservation)
when {
    resource.cabin_mismatch == true
};

permit (principal is Agent, action == Action::"book_reservation", resource is Reservation);

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.passenger_count > 5
};

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.cabin_mismatch == true
};

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.payment_not_in_profile == true
};

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.certificate_count > 1
};

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.credit_card_count > 1
};

forbid (principal is Agent, action == Action::"book_reservation", resource is Reservation)
when {
    resource.gift_card_count > 3
};

permit (principal is Agent, action == Action::"get_user_details", resource is User);

permit (principal is Agent, action == Action::"get_reservation_details", resource is Reservation);

permit (principal is Agent, action == Action::"search_direct_flight", resource is Flight);

permit (principal is Agent, action == Action::"search_onestop_flight", resource is Flight);

permit (principal is Agent, action == Action::"get_flight_status", resource is Status);

permit (principal is Agent, action == Action::"list_all_airports", resource is Airports);

permit (principal is Agent, action == Action::"calculate", resource is System);

permit (principal is Agent, action == Action::"update_reservation_passengers", resource is Reservation);

permit (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    principal.cannot_handle == true
};

permit (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    resource.any_flight_already_flown == true
};

forbid (principal is Agent, action == Action::"transfer_to_human_agents", resource is Reservation)
when {
    principal.cannot_handle == false &&
    resource.any_flight_already_flown == false
};