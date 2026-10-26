// =============================================================================
// READ & QUERY TOOLS (Safe operations permitted for Agent)
// =============================================================================

permit (
    principal is Agent,
    action in [
        Action::"get_order_details",
        Action::"provide_order_information"
    ],
    resource is Order
);

permit (
    principal is Agent,
    action in [
        Action::"get_user_details",
        Action::"provide_profile_information"
    ],
    resource is User
);

permit (
    principal is Agent,
    action in [
        Action::"get_product_details",
        Action::"get_item_details",
        Action::"list_all_product_types",
        Action::"provide_product_information"
    ],
    resource
);

permit (
    principal is Agent,
    action in [
        Action::"find_user_id_by_email",
        Action::"find_user_id_by_name_zip",
        Action::"authenticate_user_identity"
    ],
    resource is User
);

permit (
    principal is Agent,
    action == Action::"calculate",
    resource
);


// =============================================================================
// STATE-CHANGING / MUTATION PERMITS
// =============================================================================

permit (
    principal,
    action in [
        Action::"modify_default_user_address",
        Action::"modify_user_address"
    ],
    resource
)
when {
    principal is Agent &&
    resource is User &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"pending" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"modify_order_shipping_address",
        Action::"modify_pending_order_address"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"pending" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"pending" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"pending" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"return_order",
        Action::"return_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"delivered" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has authenticated_user &&
    context.conversation.authenticated_user == resource.user &&
    resource.status == OrderStatus::"delivered" &&
    context.action_details_listed == true &&
    context.explicit_user_confirmation == true
};

permit (
    principal,
    action == Action::"transfer_to_human_agents",
    resource
)
when {
    principal is Agent &&
    resource is Conversation &&
    context.request_can_be_handled_in_scope == false
};


// =============================================================================
// FORBID POLICIES (Restrictions & Safety Guards)
// =============================================================================

forbid (
    principal,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order",
        Action::"modify_order_shipping_address",
        Action::"modify_pending_order_address",
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment",
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    resource.modify_tool_called == true
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    resource.exchange_tool_called == true
};

forbid (
    principal,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method == resource.payment_method
};

forbid (
    principal,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card" &&
    !(context.conversation.selected_payment_method has balance_cents)
};

forbid (
    principal,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card" &&
    context.conversation.selected_payment_method has balance_cents &&
    context.conversation.selected_payment_method.balance_cents < resource.total_cents
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    !(context.original_item in resource.variant_items)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    !(context.conversation has items_to_change)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has items_to_change &&
    !(context.original_item in context.conversation.items_to_change)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.replacement_item.is_available == false
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.replacement_item.product != context.original_item.product
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.replacement_item.options == context.original_item.options
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    resource has item_modification_price_difference &&
    resource.item_modification_price_difference != 0 &&
    !(context.conversation has selected_payment_method)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card" &&
    !(context.conversation.selected_payment_method has balance_cents)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card" &&
    !(resource has item_modification_price_difference)
};

forbid (
    principal,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card" &&
    context.conversation.selected_payment_method has balance_cents &&
    resource has item_modification_price_difference &&
    context.conversation.selected_payment_method.balance_cents < resource.item_modification_price_difference
};

forbid (
    principal,
    action in [
        Action::"return_order",
        Action::"return_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method != resource.payment_method &&
    !(
        context.conversation.selected_payment_method in resource.user.payment_methods &&
        context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card"
    )
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    !(context.exchange_line_item.original_item in resource.variant_items)
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    !(context.conversation has exchange_line_items)
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has exchange_line_items &&
    !(context.exchange_line_item in context.conversation.exchange_line_items)
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    !(context.conversation has all_exchange_items_provided_confirmed)
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has all_exchange_items_provided_confirmed &&
    context.conversation.all_exchange_items_provided_confirmed == false
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.exchange_line_item.replacement_item.is_available == false
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.exchange_line_item.replacement_item.product != context.exchange_line_item.original_item.product
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.exchange_line_item.replacement_item.options == context.exchange_line_item.original_item.options
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    resource has exchange_price_difference &&
    resource.exchange_price_difference != decimal("0.00") &&
    !(context.conversation has selected_payment_method)
};

forbid (
    principal,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource
)
when {
    principal is Agent &&
    resource is Order &&
    context.conversation has selected_payment_method &&
    context.conversation.selected_payment_method.method_type == PaymentMethodType::"gift card"
};