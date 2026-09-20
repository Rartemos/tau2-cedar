// Cancellation is fail-closed: Cedar must have a complete Reservation entity
// and must positively establish an allowed cancellation condition.
permit (principal is Agent, action == Action::"cancel_reservation", resource is Reservation)
when {
    resource.any_flight_already_flown == false &&
    (
        resource.booked_within_24hrs == true ||
        resource.airline_cancelled == true ||
        resource.cabin == "business" ||
        (
            resource.insurance == "yes" &&
            (
                resource.cancellation_reason == "health" ||
                resource.cancellation_reason == "weather"
            )
        )
    )
};

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

permit (principal is Agent, action == Action::"send_certificate", resource)
when {
    context.confirmed == true &&
    (
        context.membership == "silver" ||
        context.membership == "gold" ||
        context.insurance == "yes" ||
        context.cabin == "business"
    )
};

// The current tool call must carry verified confirmation context. If that
// fact cannot be established, compensation is explicitly denied.
forbid (principal is Agent, action == Action::"send_certificate", resource)
when {
    context.confirmed == false
};

forbid (principal is Agent, action == Action::"send_certificate", resource)
when {
    context.membership == "regular" &&
    context.insurance == "no" &&
    (
        context.cabin == "economy" ||
        context.cabin == "basic_economy"
    )
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
    context.new_baggage_count < resource.total_baggages
};

permit (principal is Agent, action == Action::"update_reservation_passengers", resource is Reservation);

permit (principal is Agent, action == Action::"book_reservation", resource);

forbid (principal is Agent, action == Action::"book_reservation", resource)
when {
    context.passenger_count > 5
};

forbid (principal is Agent, action == Action::"book_reservation", resource)
when {
    context.certificate_count > 1
};

forbid (principal is Agent, action == Action::"book_reservation", resource)
when {
    context.credit_card_count > 1
};

forbid (principal is Agent, action == Action::"book_reservation", resource)
when {
    context.gift_card_count > 3
};

permit (principal is Agent, action == Action::"get_user_details", resource is User);

permit (principal is Agent, action == Action::"get_reservation_details", resource is Reservation);

permit (principal is Agent, action == Action::"list_all_airports", resource);

permit (principal is Agent, action == Action::"search_direct_flight", resource);

permit (principal is Agent, action == Action::"search_onestop_flight", resource);

permit (principal is Agent, action == Action::"get_flight_status", resource is Flight);

permit (principal is Agent, action == Action::"calculate", resource);

permit (principal is Agent, action == Action::"transfer_to_human_agents", resource);
