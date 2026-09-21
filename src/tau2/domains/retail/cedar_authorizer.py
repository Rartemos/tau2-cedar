from typing import Any

from tau2.domains.retail.data_model import RetailDB, GiftCard, Order, User, PaymentMethod
from tau2.environment.cedar_authorization import CedarAuthorizer

class RetailCedarAuthorizer(CedarAuthorizer):
    """Retail domain Cedar authorizer.
    
    Extracts live entities from RetailDB to provide dynamic attributes
    (such as order status, cancellation reason, payment method validity,
    item availability, etc.) required by the retail Cedar policies.
    """
    
    def __init__(
        self,
        db: RetailDB | None = None,
        policy_name: str | None = None,
    ) -> None:
        super().__init__(
            domain_name="retail",
            policy_name=policy_name or "retail.cedar",
            db=db,
        )
    
    def _generate_domain_entities(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extracts dynamic Order and User entities from RetailDB.
        
        Args:
            tool_name (str): The name of the tool being executed.
            arguments (dict[str, Any]): Arguments passed to the tool call.
                        
        Returns:
            list[dict[str, Any]]: The domain entity definitions formatted for Cedar.
        """
        entities: list[dict[str, Any]] = []
        
        if not self.db or not isinstance(self.db, RetailDB):
            return entities
        
        order_id: str | None = arguments.get("order_id")
        user_id: str | None = arguments.get("user_id")
        
        # Extract order entity
        if order_id and order_id in self.db.orders:
            order: Order = self.db.orders[order_id]
            user: User | None = self.db.users.get(order.user_id) 
        
            # Identify original payment method.
            original_payment_method_id: str | None = (
                order.payment_history[0].payment_method_id
                if order.payment_history
                else None
            )
            
            # Check argument payment method if provided
            arg_pm_id: str | None = arguments.get("payment_method_id")
            is_gift_card: bool = False
            gift_card_balance: float = 0.0
            is_original_payment: bool = False
            is_same_as_current: bool = False
            
            if arg_pm_id:
                is_original_payment = (arg_pm_id == original_payment_method_id)
                is_same_as_current = (arg_pm_id == original_payment_method_id)
                
                if user:
                    pm: PaymentMethod | None = user.payment_methods.get(arg_pm_id)
                    if isinstance(pm, GiftCard):
                        is_gift_card = True
                        gift_card_balance = float(pm.balance)
            
            # Validate items if exchange, return or modification is being attempted
            if "item_ids" in arguments:
                item_ids: list[str] = arguments.get("item_ids", [])
                new_item_ids: list[str] = arguments.get("new_item_ids", [])
                all_order_item_ids: list[str] = [item.item_id for item in order.items]
            
                items_exist_in_order: bool = bool(
                    item_ids
                    and all(
                        item_ids.count(iid) <= all_order_item_ids.count(iid)
                        for iid in set(item_ids)
                    )
                )
                item_count_matches: bool = len(item_ids) == len(new_item_ids)
            else:
                items_exist_in_order = True
                item_count_matches = True
            
            # Build dynamic order entity attributes expected by retail.cedar
            attrs: dict[str, Any] = {
                "status": str(order.status),
                "is_pending": order.status == "pending",
                "is_delivered": order.status == "delivered",
                "user_id": str(order.user_id),
                "items_count": len(order.items),
                "payment_history_count": len(order.payment_history),
                "original_payment_method_id": str(original_payment_method_id or ""),
                "is_original_payment": is_original_payment,
                "is_same_as_current_payment": is_same_as_current,
                "is_gift_card": is_gift_card,
                "gift_card_balance": gift_card_balance,
                "items_exist_in_order": items_exist_in_order,
                "item_count_matches": item_count_matches,
                "has_been_modified_or_cancelled": order.status in (
                    "cancelled",
                    "pending (item modified)",
                    "exchange requested",
                    "return requested",
                ),
            }
            
            # Tool-specific contextual arguments
            if "reason" in arguments:
                attrs["cancellation_reason"] = arguments["reason"]
            
            elif order.cancel_reason:
                attrs["cancellation_reason"] = order.cancel_reason
            
            else:
                attrs["cancellation_reason"] = ""
            
            entities.append({
                "uid": {"type": "Order", "id": order_id},
                "attrs": attrs,
                "parents": [],
            })
            
            # If user_id wasn't explicitly supplied, populate user entity from order
            if not user_id:
                user_id = order.user_id
            
        # Extract user entity
        if user_id and user_id in self.db.users:
            user_obj: User = self.db.users[user_id]
            user_attrs: dict[str, Any] = {
                "email": str(user_obj.email),
                "orders_count": len(user_obj.orders),
                "payment_methods_count": len(user_obj.payment_methods),
            }
            entities.append({
                "uid": {"type": "User", "id": user_id},
                "attrs": user_attrs,
                "parents": [],
            })

        return entities
    
    def _determine_resource(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Determines the Cedar Resource identifier for the retail domain.
            
        Args:
            tool_name (str): The name of the tool being called.
            arguments (dict[str, Any]): The arguments passed to the tool.
            
        Returns:
            str: The formatted Cedar Resource ID string.
        """
        if tool_name == "transfer_to_human_agents":
            order_id: str | None = arguments.get("order_id")
            if order_id:
                return f'Order::"{order_id}"'
            return 'RetailContext::"transfer"'
        return super()._determine_resource(tool_name, arguments)