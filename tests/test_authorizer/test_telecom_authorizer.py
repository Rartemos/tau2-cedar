import pytest
from tau2.domains.telecom.authorizer import TelecomCedarAuthorizer
from tau2.domains.telecom.data_model import BillStatus, LineStatus
from tau2.domains.telecom.environment import TelecomEnvironment, get_environment
from tau2.domains.telecom.user_data_model import PaymentRequest

@pytest.fixture(scope="module")
def env() -> TelecomEnvironment:
    """Load telecom environment with default TelecomDB and TelecomUserDB."""
    return get_environment(cedar_policy="permit_all") # Temporarily use permit_all until policies are set

@pytest.fixture(scope="module")
def authorizer(env: TelecomEnvironment) -> TelecomCedarAuthorizer:
    assert isinstance(env.cedar_authorizer, TelecomCedarAuthorizer)
    return env.cedar_authorizer

def _find_entity(entities: list[dict], entity_type: str, entity_id: str | None = None) -> dict | None:
    """Helper to locate an extracted Cedar entity by type (and optional ID)."""
    for entity in entities:
        uid = entity["uid"]
        if uid["type"] == entity_type and (entity_id is None or uid["id"] == entity_id):
            return entity
    return None

def test_agent_entity_extraction_refuel_and_line_lookup(
    env: TelecomEnvironment, authorizer: TelecomCedarAuthorizer
):
    """Verify refuel_data extracts Line, owning Customer (via parent), Plan, and decimal attrs."""
    line = next(l for l in env.tools.db.lines if l.status == LineStatus.ACTIVE)
    owner = next(c for c in env.tools.db.customers if line.line_id in c.line_ids)
    
    authorizer._current_requestor = "assistant"
    entities = authorizer.build_entities(
        "refuel_data",
        {"customer_id": owner.customer_id, "line_id": line.line_id, "gb_amount": 1.5},
    )
    
    customer_entity = _find_entity(entities, "Customer", owner.customer_id)
    line_entity = _find_entity(entities, "Line", line.line_id)
    plan_entity = _find_entity(entities, "Plan", line.plan_id)
    
    assert _find_entity(entities, "Agent", "assistant") is not None
    assert customer_entity is not None
    assert customer_entity["attrs"]["account_status"] == owner.account_status.value
    assert "__extn" in customer_entity["attrs"]["goodwill_credit_used_this_year"]
    
    assert line_entity is not None
    assert {"type": "Customer", "id": owner.customer_id} in line_entity["parents"]
    assert line_entity["attrs"]["requested_refuel_gb"] == {
        "__extn": {"fn": "decimal", "arg": "1.50"}
    }
    
    assert plan_entity is not None
    assert "__extn" in plan_entity["attrs"]["data_limit_gb"]
    
    if line.device_id:
        assert _find_entity(entities, "Device", line.device_id) is not None
        
def test_agent_entity_extraction_bill_and_resource_precedence(
    env: TelecomEnvironment, authorizer: TelecomCedarAuthorizer
):
    """Verify Bill entity extraction and that bill_id takes precedence over customer_id."""
    bill = env.tools.db.bills[0]
    args = {"customer_id": bill.customer_id, "bill_id": bill.bill_id}
    
    result = authorizer.authorize_tool_call("send_payment_request", "assistant", args)
    assert result["cedar_request"]["resource"] == f'Bill::"{bill.bill_id}"'
    assert result["cedar_eval_errors"] == []
    
    entities = authorizer.build_entities("send_payment_request", args)
    bill_ent = _find_entity(entities, "Bill", bill.bill_id)
    customer_ent = _find_entity(entities, "Customer", bill.customer_id)
    
    assert bill_ent is not None
    assert bill_ent["attrs"]["is_overdue"] is (bill.status == BillStatus.OVERDUE)
    assert {"type": "Customer", "id": bill.customer_id} in bill_ent["parents"]
    assert customer_ent is not None
    
def test_agent_lookup_by_phone_name_and_details_id(
    env: TelecomEnvironment, authorizer: TelecomCedarAuthorizer
):
    """Verify phone fallback via line, name+dob lookup, and get_details_by_id prefixes."""
    line = env.tools.db.lines[0]
    owner = next(c for c in env.tools.db.customers if line.line_id in c.line_ids)
    
    # 1. Phone lookup using line phone number
    res_phone = authorizer.authorize_tool_call(
        "get_customer_by_phone", "assistant", {"phone_number": line.phone_number}
    )
    assert res_phone["cedar_request"]["resource"] == f'Customer::"{owner.customer_id}"'
    
    # 2. Name + DOB lookup
    res_name = authorizer.authorize_tool_call(
        "get_customer_by_name",
        "assistant",
        {"full_name": owner.full_name, "dob": owner.date_of_birth},
    )
    assert res_name["cedar_request"]["resource"] == f'Customer::"{owner.customer_id}"'
    
    # 3. get_details_by_id across C/L/B/P/D prefixes
    sample_ids = [
        ("C", owner.customer_id, "Customer"),
        ("L", line.line_id, "Line"),
        ("B", env.tools.db.bills[0].bill_id, "Bill"),
        ("P", env.tools.db.plans[0].plan_id, "Plan"),
        ("D", env.tools.db.devices[0].device_id, "Device"),
    ]
    for _, obj_id, expected_type in sample_ids:
        res_id = authorizer.authorize_tool_call(
            "get_details_by_id", "assistant", {"id": obj_id}
        )
        assert res_id["cedar_request"]["resource"] == f'{expected_type}::"{obj_id}"'
        ents = authorizer.build_entities("get_details_by_id", {"id": obj_id})
        assert _find_entity(ents, expected_type, obj_id) is not None
        
def test_agent_malformed_gb_amount_guard(
    env: TelecomEnvironment, authorizer: TelecomCedarAuthorizer
):
    """Verify non-numeric or None gb_amount safely defaults to 0.00."""
    line = env.tools.db.lines[0]
    authorizer._current_requestor = "assistant"
    entities = authorizer.build_entities(
        "refuel_data", {"line_id": line.line_id, "gb_amount": None}
    )
    line_ent = _find_entity(entities, "Line", line.line_id)
    assert line_ent is not None
    assert line_ent["attrs"]["requested_refuel_gb"] == {
        "__extn": {"fn": "decimal", "arg": "0.00"}
    }
def test_user_entity_extraction_device_surroundings_app_and_payment(
    env: TelecomEnvironment, authorizer: TelecomCedarAuthorizer
):
    """Verify user-side entity extraction for Device, Surroundings, App, and PaymentRequest."""
    original_payment = env.user_tools.db.surroundings.payment_request
    try:
        env.user_tools.db.surroundings.payment_request = PaymentRequest(
            bill_id="B_TEST_1", amount_due=42.50, paid=False
        )
        # User diagnostic & device tools
        res_device = authorizer.authorize_tool_call("toggle_data", "user", {})
        assert res_device["cedar_request"]["principal"] == 'User::"user"'
        assert res_device["cedar_request"]["resource"] == 'Device::"phone"'
        
        user_ents = authorizer.build_entities("toggle_data", {})
        assert _find_entity(user_ents, "Agent") is None
        assert _find_entity(user_ents, "User", "user") is not None
        assert _find_entity(user_ents, "Surroundings", "current") is not None
        assert _find_entity(user_ents, "Device", "phone") is not None
        
        # App entity (can_send_mms defaults app_name to "messaging")
        res_mms = authorizer.authorize_tool_call("can_send_mms", "user", {})
        assert res_mms["cedar_request"]["resource"] == 'App::"messaging"'
        mms_ents = authorizer.build_entities("can_send_mms", {})
        app_ent = _find_entity(mms_ents, "App", "messaging")
        assert app_ent is not None
        assert app_ent["attrs"]["installed"] is True
        
        # PaymentRequest entity
        res_pay = authorizer.authorize_tool_call("make_payment", "user", {})
        assert res_pay["cedar_request"]["resource"] == 'PaymentRequest::"B_TEST_1"'
        pay_ents = authorizer.build_entities("make_payment", {})
        pay_ent = _find_entity(pay_ents, "PaymentRequest", "B_TEST_1")
        assert pay_ent is not None
        assert pay_ent["attrs"]["paid"] is False
    finally:
        env.user_tools.db.surroundings.payment_request = original_payment
        
def test_solo_mode_user_tool_keeps_agent_and_extracts_device(
    authorizer: TelecomCedarAuthorizer,
):
    """Verify assistant calling a user tool (solo mode) extracts Device/Surroundings."""
    res = authorizer.authorize_tool_call("toggle_roaming", "assistant", {})
    assert res["cedar_request"]["principal"] == 'Agent::"assistant"'
    assert res["cedar_request"]["resource"] == 'Device::"phone"'
    
    entities = authorizer.build_entities("toggle_roaming", {})
    assert _find_entity(entities, "Agent", "assistant") is not None
    assert _find_entity(entities, "User") is None
    assert _find_entity(entities, "Device", "phone") is not None
    assert _find_entity(entities, "Surroundings", "current") is not None