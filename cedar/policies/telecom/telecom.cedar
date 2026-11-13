// ==============================================================================
// AGENT POLICIES (TelecomTools)
// ==============================================================================

// Customer & Account Lookups (Read Operations)
permit (
    principal is Agent,
    action in [
        Action::"get_customer_by_phone",
        Action::"get_customer_by_id",
        Action::"get_customer_by_name",
        Action::"get_bills_for_customer"
    ],
    resource is Customer
);

// Generic Entity Details Lookup (C/L/B/P/D)
permit (
    principal is Agent,
    action == Action::"get_details_by_id",
    resource
);

// Line Usage Lookup
permit (
    principal is Agent,
    action == Action::"get_data_usage",
    resource is Line
);

// Plan Lookup
permit (
    principal is Agent,
    action == Action::"get_available_plan_ids",
    resource
);

// Transfer to Human Agents
permit (
    principal is Agent,
    action == Action::"transfer_to_human_agents",
    resource is System
);

// Roaming Management
permit (
    principal is Agent,
    action in [
        Action::"enable_roaming",
        Action::"disable_roaming"
    ],
    resource is Line
);

// Line Suspension: Line must be ACTIVE to suspend
permit (
    principal is Agent,
    action in [
        Action::"suspend_line",
        Action::"suspend_line_for_overdue_bill"
    ],
    resource is Line
) when {
    resource.status == "Active"
};

forbid (
    principal is Agent,
    action in [
        Action::"suspend_line",
        Action::"suspend_line_for_overdue_bill"
    ],
    resource is Line
) when {
    resource.status != "Active"
};

// Resume Line:
// - Line must be currently SUSPENDED
// - Line contract must NOT have ended
permit (
    principal is Agent,
    action == Action::"resume_line",
    resource is Line
) when {
    resource.status == "Suspended"
};

forbid (
    principal is Agent,
    action == Action::"resume_line",
    resource is Line
) when {
    resource.status != "Suspended"
};

forbid (
    principal is Agent,
    action == Action::"resume_line",
    resource is Line
) when {
    resource.contract_ended == true
};

// Data Refueling:
// - Line must be ACTIVE
// - Requested refueling must be > 0.00 and <= 2.00 GB
permit (
    principal is Agent,
    action == Action::"refuel_data",
    resource is Line
) when {
    resource.status == "Active" &&
    resource.requested_refuel_gb.greaterThan(decimal("0.00")) &&
    resource.requested_refuel_gb.lessThanOrEqual(decimal("2.00"))
};

forbid (
    principal is Agent,
    action == Action::"refuel_data",
    resource is Line
) when {
    resource.status != "Active" ||
    resource.requested_refuel_gb.lessThanOrEqual(decimal("0.00")) ||
    resource.requested_refuel_gb.greaterThan(decimal("2.00"))
};

// Send Payment Request:
// - Bill must be OVERDUE
permit (
    principal is Agent,
    action == Action::"send_payment_request",
    resource is Bill
) when {
    resource.is_overdue == true
};

forbid (
    principal is Agent,
    action == Action::"send_payment_request",
    resource is Bill
) when {
    resource.is_overdue == false
};

// ==============================================================================
// USER POLICIES (TelecomUserTools)
// ==============================================================================

// Surroundings / Diagnostic Actions
permit (
    principal is User,
    action in [
        Action::"check_status_bar",
        Action::"check_network_status",
        Action::"check_network_mode_preference",
        Action::"check_data_restriction_status",
        Action::"check_apn_settings",
        Action::"check_wifi_status",
        Action::"check_wifi_calling_status",
        Action::"check_vpn_status",
        Action::"check_sim_status",
        Action::"check_installed_apps",
        Action::"run_speed_test"
    ],
    resource is Surroundings
);

// App Diagnostic & Permission Actions
permit (
    principal is User,
    action in [
        Action::"check_app_status",
        Action::"check_app_permissions",
        Action::"grant_app_permission",
        Action::"can_send_mms"
    ],
    resource is App
);

// Device Control Actions
permit (
    principal is User,
    action in [
        Action::"toggle_data",
        Action::"toggle_roaming",
        Action::"toggle_wifi",
        Action::"toggle_airplane_mode",
        Action::"toggle_data_saver_mode",
        Action::"toggle_wifi_calling",
        Action::"set_network_mode_preference",
        Action::"connect_vpn",
        Action::"disconnect_vpn",
        Action::"set_apn_settings",
        Action::"reset_apn_settings",
        Action::"reseat_sim_card",
        Action::"reboot_device"
    ],
    resource is Device
);

// User Payment Actions
permit (
    principal is User,
    action in [
        Action::"check_payment_request",
        Action::"make_payment"
    ],
    resource is PaymentRequest
);
