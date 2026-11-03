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
        Action::"list_all_product_types",
        Action::"provide_product_information",
        Action::"calculate"
    ],
    resource
);

permit (
    principal is Agent,
    action == Action::"transfer_to_human_agents",
    resource
);

permit (
    principal is Agent,
    action in [
        Action::"modify_default_user_address",
        Action::"modify_user_address"
    ],
    resource is User
);

permit (
    principal is Agent,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order"
    ],
    resource is Order
)
when { resource.is_pending == false };

forbid (
    principal is Agent,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

forbid (
    principal is Agent,
    action in [
        Action::"cancel_order",
        Action::"cancel_pending_order"
    ],
    resource is Order
)
when {
    resource.cancellation_reason != "no longer needed" &&
    resource.cancellation_reason != "ordered by mistake"
};

permit (
    principal is Agent,
    action in [
        Action::"modify_order_shipping_address",
        Action::"modify_pending_order_address"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_shipping_address",
        Action::"modify_pending_order_address"
    ],
    resource is Order
)
when { resource.is_pending == false };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_shipping_address",
        Action::"modify_pending_order_address"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

permit (
    principal is Agent,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource is Order
)
when { resource.is_pending == false };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource is Order
)
when { resource.is_same_as_current_payment == true };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_payment_method",
        Action::"modify_pending_order_payment"
    ],
    resource is Order
)
when {
    resource.is_gift_card == true &&
    resource.gift_card_balance == 0
};

permit (
    principal is Agent,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource is Order
)
when { resource.is_pending == false };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource is Order
)
when { resource.items_exist_in_order == false };

forbid (
    principal is Agent,
    action in [
        Action::"modify_order_product_item_options",
        Action::"modify_pending_order_items"
    ],
    resource is Order
)
when { resource.item_count_matches == false };

permit (
    principal is Agent,
    action in [
        Action::"return_order",
        Action::"return_delivered_order_items"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"return_order",
        Action::"return_delivered_order_items"
    ],
    resource is Order
)
when { resource.is_delivered == false };

forbid (
    principal is Agent,
    action in [
        Action::"return_order",
        Action::"return_delivered_order_items"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

permit (
    principal is Agent,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource is Order
);

forbid (
    principal is Agent,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource is Order
)
when { resource.is_delivered == false };

forbid (
    principal is Agent,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource is Order
)
when { resource.has_been_modified_or_cancelled == true };

forbid (
    principal is Agent,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource is Order
)
when { resource.items_exist_in_order == false };

forbid (
    principal is Agent,
    action in [
        Action::"exchange_order",
        Action::"exchange_delivered_order_items"
    ],
    resource is Order
)
when { resource.item_count_matches == false };