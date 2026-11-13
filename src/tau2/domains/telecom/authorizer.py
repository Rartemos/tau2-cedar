from pathlib import Path
from typing import Any
from tau2.domains.telecom.data_model import (
    Bill,
    BillStatus,
    Customer,
    Device,
    Line,
    Plan,
    TelecomDB,
)
from tau2.domains.telecom.user_data_model import TelecomUserDB
from tau2.domains.telecom.utils import get_today
from tau2.environment.authorizer import CedarAuthorizer


class TelecomCedarAuthorizer(CedarAuthorizer):
    """Cedar authorizer for the Telecom domain.
    
    Handles policy evaluation and entity construction for both:
    1. Agent actions (TelecomTools): Administrative actions such as line suspension,
       resume, data refuels, roaming toggles, bill payment requests, and transfers.
    2. User actions (TelecomUserTools): Client device toggles such as airplane mode,
       data/roaming toggles, APN changes, VPN configurations, and bill payments.
       
    Principal and resource resolution is routed based on the requestor role:
    - ``Agent::"assistant"`` evaluates against ``TelecomDB``.
    - ``User::"user"`` evaluates against ``TelecomUserDB``.
    """
    
    USER_DEVICE_TOOLS: set[str] = {
        "toggle_data",
        "toggle_roaming",
        "toggle_wifi",
        "toggle_airplane_mode",
        "toggle_data_saver_mode",
        "toggle_wifi_calling",
        "set_network_mode_preference",
        "connect_vpn",
        "disconnect_vpn",
        "set_apn_settings",
        "reset_apn_settings",
        "reseat_sim_card",
        "reboot_device",
    }
    USER_SURROUNDINGS_TOOLS: set[str] = {
        "check_status_bar",
        "check_network_status",
        "check_network_mode_preference",
        "check_data_restriction_status",
        "check_apn_settings",
        "check_wifi_status",
        "check_wifi_calling_status",
        "check_vpn_status",
        "check_sim_status",
        "check_installed_apps",
        "run_speed_test",
    }
    USER_APP_TOOLS: set[str] = {
        "check_app_status",
        "check_app_permissions",
        "grant_app_permission",
        "can_send_mms",
    }
    USER_PAYMENT_TOOLS: set[str] = {
        "check_payment_request",
        "make_payment",
    }
    ALL_USER_TOOLS: set[str] = (
        USER_DEVICE_TOOLS | USER_SURROUNDINGS_TOOLS | USER_APP_TOOLS | USER_PAYMENT_TOOLS
    )
    
    def __init__(
        self,
        db: TelecomDB | None = None,
        user_db: TelecomUserDB | None = None,
        policy_path: str | Path | None = None,
        schema_path: str | Path | None = None,
        **kwargs,
    ) -> None:
        """Initialize the telecom authorizer.
            
        Args:
            db: TelecomDB instance for entity extraction.
            user_db: TelecomUserDB instance for user entity extraction.
            policy_path: Path to the Cedar policy file. Defaults to ``telecom.cedar``.
            schema_path: Path to the Cedar schema file, if provided.
            **kwargs: Additional keyword arguments forwarded to CedarAuthorizer.
        """
        super().__init__(
            domain_name="telecom",
            db=db,
            policy_path=policy_path,
            schema_path=schema_path,
            **kwargs,
        )
        self.db: TelecomDB | None = db
        self.user_db: TelecomUserDB | None = user_db
        self._current_requestor: str = "assistant"
        
    def build_entities(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Cedar entities for agent or user tool calls.
        
        Args:
            tool_name: The name of the tool call.
            arguments: The raw tool parameters.
                            
        Returns:
            A list of Cedar entity dictionaries.
        """
        base_entities: list[dict[str, Any]] = super().build_entities(tool_name, arguments)
        
        if self._current_requestor.lower() == "user" or tool_name in self.ALL_USER_TOOLS:
            if self._current_requestor.lower() == "user":
                base_entities = [e for e in base_entities if e["uid"]["type"] != "Agent"]
            return self._build_user_entities(base_entities, tool_name, arguments)
        return self._build_agent_entities(base_entities, arguments)
        
    def _build_agent_entities(
        self,
        entities: list[dict[str, Any]],
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Cedar entities from TelecomDB for agent tool calls.
        
        Resolves Customer, Line, Bill, and Plan entities from arguments.
        Supports cross-lookup (e.g. finding Customer from line_id or bill_id).
        
        Args:
            entities: Existing base entities slice containing principal entities.
            arguments: Parameters passed to the agent tool call.
            
        Returns:
            The expanded entity slice.
        """
        if not isinstance(self.db, TelecomDB):
            return entities
        
        db: TelecomDB = self.db
        
        phone_number: str | None = arguments.get("phone_number")
        customer_id: str | None = arguments.get("customer_id")
        line_id: str | None = arguments.get("line_id")
        bill_id: str | None = arguments.get("bill_id")
        plan_id: str | None = None
        device_id: str | None = None
        
        # Support get_details_by_id(id=...) prefix conventions (C/L/B/P/D)
        details_id: str | None = arguments.get("id")
        if isinstance(details_id, str):
            if details_id.startswith("C") and not customer_id:
                customer_id = details_id
            elif details_id.startswith("L") and not line_id:
                line_id = details_id
            elif details_id.startswith("B") and not bill_id:
                bill_id = details_id
            elif details_id.startswith("P"):
                plan_id = details_id
            elif details_id.startswith("D"):
                device_id = details_id
        
        # Resolve Line if line_id or phone_number is present
        target_line: Line | None = None
        if line_id:
            target_line = next((l for l in db.lines if l.line_id == line_id), None)
        elif phone_number:
            target_line = next((l for l in db.lines if l.phone_number == phone_number), None)
            
        # Resolve Customer (ID -> name+dob -> phone_number -> line/bill ownership)
        target_customer: Customer | None = None
        if customer_id:
            target_customer = next((c for c in db.customers if c.customer_id == customer_id), None)
        elif arguments.get("full_name") and arguments.get("dob"):
            full_name = str(arguments["full_name"]).lower()
            dob = str(arguments["dob"])
            target_customer = next(
                (
                    c for c in db.customers 
                    if c.full_name.lower() == full_name and c.date_of_birth == dob
                ),
                None,
            )
        elif phone_number:
            target_customer = next((c for c in db.customers if c.phone_number == phone_number), None)
        if target_customer is None and target_line:
            target_customer = next(
                (c for c in db.customers if target_line.line_id in c.line_ids), None
            )
        if target_customer is None and bill_id:
            target_customer = next(
                (c for c in db.customers if bill_id in c.bill_ids), None
            )
            
         # Resolve Bill, Plan, and Device
        target_bill: Bill | None = (
            next((b for b in db.bills if b.bill_id == bill_id), None) if bill_id else None
        )
        effective_plan_id = plan_id or (target_line.plan_id if target_line else None)
        target_plan: Plan | None = (
            next((p for p in db.plans if p.plan_id == effective_plan_id), None)
            if effective_plan_id
            else None
        )
        effective_device_id = device_id or (target_line.device_id if target_line else None)
        target_device: Device | None = (
            next((d for d in db.devices if d.device_id == effective_device_id), None)
            if effective_device_id
            else None
        )
        
        # Build Cedar Customer Entity 
        if target_customer:
            has_overdue_bill = any(
                b.status == BillStatus.OVERDUE
                for b in db.bills
                if b.bill_id in target_customer.bill_ids
            )
            entities.append({
                "uid": {"type": "Customer", "id": target_customer.customer_id},
                "attrs": {
                    "account_status": str(target_customer.account_status.value),
                    "num_lines": len(target_customer.line_ids),
                    "num_bills": len(target_customer.bill_ids),
                    "has_payment_method": len(target_customer.payment_methods) > 0,
                    "has_overdue_bill": has_overdue_bill,
                    "goodwill_credit_used_this_year": {
                        "__extn": {
                            "fn": "decimal",
                            "arg": f"{target_customer.goodwill_credit_used_this_year:.2f}",
                        }
                    },
                },
                "parents": [],
            })
            
        # Build Cedar Line Entity
        if target_line:
            line_parents = (
                [{"type": "Customer", "id": target_customer.customer_id}]
                if target_customer
                else []
            )
            contract_ended = (
                target_line.contract_end_date is not None
                and target_line.contract_end_date < get_today()
            )
            raw_gb = arguments.get("gb_amount", 0.0)
            try:
                requested_gb = float(raw_gb) if raw_gb is not None else 0.0
            except (TypeError, ValueError):
                requested_gb = 0.0
            entities.append({
                "uid": {"type": "Line", "id": target_line.line_id},
                "attrs": {
                    "status": str(target_line.status.value),
                    "roaming_enabled": bool(target_line.roaming_enabled),
                    "contract_ended": contract_ended,
                    "data_used_gb": {"__extn": {"fn": "decimal", "arg": f"{target_line.data_used_gb:.2f}"}},
                    "data_refueling_gb": {"__extn": {"fn": "decimal", "arg": f"{target_line.data_refueling_gb:.2f}"}},
                    "plan_id": str(target_line.plan_id),
                    "requested_refuel_gb": {"__extn": {"fn": "decimal", "arg": f"{requested_gb:.2f}"}},
                },
                "parents": line_parents,
            })
            
        # Build Cedar Bill Entity
        if target_bill:
            bill_parents = (
                [{"type": "Customer", "id": target_customer.customer_id}]
                if target_customer
                else []
            )
            entities.append({
                "uid": {"type": "Bill", "id": target_bill.bill_id},
                "attrs": {
                    "status": str(target_bill.status.value),
                    "is_overdue": target_bill.status == BillStatus.OVERDUE,
                    "total_due": {"__extn": {"fn": "decimal", "arg": f"{target_bill.total_due:.2f}"}},
                    "customer_id": str(target_bill.customer_id),
                },
                "parents": bill_parents,
            })
            
        # Build Cedar Plan Entity 
        if target_plan:
            entities.append({
                "uid": {"type": "Plan", "id": target_plan.plan_id},
                "attrs": {
                    "data_limit_gb": {"__extn": {"fn": "decimal", "arg": f"{target_plan.data_limit_gb:.2f}"}},
                    "price_per_month": {"__extn": {"fn": "decimal", "arg": f"{target_plan.price_per_month:.2f}"}},
                    "data_refueling_price_per_gb": {
                        "__extn": {
                            "fn": "decimal",
                            "arg": f"{target_plan.data_refueling_price_per_gb:.2f}",
                        }
                    },
                },
                "parents": [],
            })
            
        # Build Device Entity (agent DB)
        if target_device:
            entities.append({
                "uid": {"type": "Device", "id": target_device.device_id},
                "attrs": {
                    "device_type": str(target_device.device_type.value),
                    "is_esim_capable": bool(target_device.is_esim_capable),
                    "activated": bool(target_device.activated),
                },
                "parents": [],
            })
            
        return entities
    
    def _build_user_entities(
        self,
        entities: list[dict[str, Any]],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build Cedar entities from TelecomUserDB for user tool calls.
        
        Exposes surroundings (line_active, roaming_allowed, abroad, data exceeded)
        and device state (airplane_mode, data_enabled, roaming_enabled) for policies.
        
        Args:
            entities: Existing base entities slice containing principal entities.
            tool_name: The name of the tool call.
            arguments: The raw tool parameters.
            
        Returns:
            The expanded entity slice with Surroundings and Device.
        """
        if self._current_requestor.lower() == "user":
            entities.append({
                "uid": {"type": "User", "id": self._current_requestor},
                "attrs": {},
                "parents": [],
            })
        
        if not isinstance(self.user_db, TelecomUserDB):
            return entities
        
        surroundings = self.user_db.surroundings
        device = self.user_db.device
        payment_req = surroundings.payment_request
        amount_due = payment_req.amount_due if payment_req else 0.0
        
        entities.append({
            "uid": {"type": "Surroundings", "id": "current"},
            "attrs": {
                "line_active": bool(surroundings.line_active),
                "is_abroad": bool(surroundings.is_abroad),
                "roaming_allowed": bool(surroundings.roaming_allowed),
                "mobile_data_usage_exceeded": bool(surroundings.mobile_data_usage_exceeded),
                "has_payment_request": payment_req is not None,
                "payment_amount_due": {"__extn": {"fn": "decimal", "arg": f"{amount_due:.2f}"}},
            },
            "parents": [],
        })
        
        entities.append({
            "uid": {"type": "Device", "id": "phone"},
            "attrs": {
                "airplane_mode": bool(device.airplane_mode),
                "data_enabled": bool(device.data_enabled),
                "roaming_enabled": bool(device.roaming_enabled),
                "wifi_enabled": bool(device.wifi_enabled),
                "wifi_calling_enabled": bool(device.wifi_calling_enabled),
                "vpn_connected": bool(device.vpn_connected),
                "data_saver_mode": bool(device.data_saver_mode),
                "sim_card_missing": bool(device.sim_card_missing),
                "sim_card_status": str(device.sim_card_status.value),
            },
            "parents": [],
        })
        
        app_name: str | None = arguments.get("app_name")
        if tool_name == "can_send_mms" and not app_name:
            app_name = "messaging"
            
        if app_name:
            app_status = device.app_statuses.get(app_name)
            entities.append({
                "uid": {"type": "App", "id": app_name},
                "attrs": {
                    "installed": app_status is not None,
                    "has_sms": bool(app_status.permissions.sms) if app_status else False,
                    "has_storage": bool(app_status.permissions.storage) if app_status else False,
                    "has_phone": bool(app_status.permissions.phone) if app_status else False,
                    "has_network": bool(app_status.permissions.network) if app_status else False,
                },
                "parents": [],
            })
        if payment_req is not None:
            entities.append({
                "uid": {"type": "PaymentRequest", "id": payment_req.bill_id},
                "attrs": {
                    "bill_id": str(payment_req.bill_id),
                    "amount_due": {"__extn": {"fn": "decimal", "arg": f"{payment_req.amount_due:.2f}"}},
                    "paid": bool(payment_req.paid),
                },
                "parents": [],
            })
            
        return entities
    
    def _determine_resource(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Derive the target Cedar Resource identifier for the active tool.
        
        Args:
            tool_name: The name of the tool call.
            arguments: The sanitized tool parameters.
        
        Returns:
            The formatted Cedar Resource ID string.
        """
        if tool_name in self.USER_DEVICE_TOOLS:
            return 'Device::"phone"'
        if tool_name in self.USER_SURROUNDINGS_TOOLS:
            return 'Surroundings::"current"'
        if tool_name in self.USER_APP_TOOLS:
            app_name = arguments.get("app_name") or (
                "messaging" if tool_name == "can_send_mms" else "new_context"
            )
            return f'App::"{app_name}"'
        if tool_name in self.USER_PAYMENT_TOOLS:
            if isinstance(self.user_db, TelecomUserDB) and self.user_db.surroundings.payment_request:
                return f'PaymentRequest::"{self.user_db.surroundings.payment_request.bill_id}"'
            return 'PaymentRequest::"none"'
        if tool_name == "transfer_to_human_agents":
            return 'System::"transfer"'
        if tool_name == "get_details_by_id":
            details_id = arguments.get("id")
            if isinstance(details_id, str):
                prefix_map = {
                    "C": "Customer",
                    "L": "Line",
                    "B": "Bill",
                    "P": "Plan",
                    "D": "Device",
                }
                entity_type = prefix_map.get(details_id[:1])
                if entity_type:
                    return f'{entity_type}::"{details_id}"'
        if "bill_id" in arguments and isinstance(arguments["bill_id"], str):
            return f'Bill::"{arguments["bill_id"]}"'
        if "line_id" in arguments and isinstance(arguments["line_id"], str):
            return f'Line::"{arguments["line_id"]}"'
        if "customer_id" in arguments and isinstance(arguments["customer_id"], str):
            return f'Customer::"{arguments["customer_id"]}"'
        if "phone_number" in arguments and isinstance(arguments["phone_number"], str):
            if isinstance(self.db, TelecomDB):
                phone = arguments["phone_number"]
                customer = next((c for c in self.db.customers if c.phone_number == phone), None)
                if customer is None:
                    line = next((l for l in self.db.lines if l.phone_number == phone), None)
                    if line:
                        customer = next(
                            (c for c in self.db.customers if line.line_id in c.line_ids), None
                        )
                if customer:
                    return f'Customer::"{customer.customer_id}"'
            return 'Customer::"new_context"'
        if tool_name == "get_customer_by_name":
            if isinstance(self.db, TelecomDB) and arguments.get("full_name") and arguments.get("dob"):
                full_name = str(arguments["full_name"]).lower()
                dob = str(arguments["dob"])
                customer = next(
                    (
                        c for c in self.db.customers
                        if c.full_name.lower() == full_name and c.date_of_birth == dob
                    ),
                    None,
                )
                if customer:
                    return f'Customer::"{customer.customer_id}"'
            return 'Customer::"new_context"'
        return super()._determine_resource(tool_name, arguments)
    
    def authorize_tool_call(
        self,
        tool_name: str,
        requestor: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a tool call against Cedar.
                
        Builds the authorization request and entities, 
        evaluates against Cedar, and returns a decision.
        
        Args:
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            arguments: The raw tool parameters.
                    
        Returns:
            Evaluation metadata containing ``cedar_overhead_ms``, 
            ``cedar_request``, ``cedar_policy_ids``, and ``cedar_eval_errors``.
        
        Raises:
            CedarError: If Cedar denies the request. 
        """
        self._current_requestor = requestor
        return super().authorize_tool_call(tool_name, requestor, arguments)