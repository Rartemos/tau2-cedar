import json
from pathlib import Path
from tau2.environment.cedar_logger import CedarLogger

def test_cedar_logger_writes(tmp_path: Path) -> None:
    logger: CedarLogger = CedarLogger(tmp_path / "cedar_calls.jsonl")
    logger.record_allow(
        "task_1", 
        "get_user", 
        "assistant", 
        {"user_id": "u1"}, 
        cedar_overhead_ms=12.3, 
        cedar_policy_ids=["p_allow_reads"]
    )
    logger.record_deny(
        "task_1", 
        "cancel_flight", 
        "assistant", 
        "Not authorized",
        cedar_overhead_ms=5.1, 
        cedar_policy_ids=["p_deny_cancel"]
    )
    logger.record_error(
        "task_1", 
        "update_seat", 
        "assistant", 
        ValueError("DB error")
    )
    
    lines: list[str] = (tmp_path / "cedar_calls.jsonl").read_text().splitlines()
    assert len(lines) == 3
    allow, deny, error = [json.loads(i) for i in lines]
    
    assert allow["cedar"]["decision"] == "allow"
    assert allow["call"]["tool"] == "get_user"
    assert deny["cedar"]["decision"] == "deny"
    assert deny["cedar"]["feedback"] == "Not authorized"
    assert error["cedar"]["decision"] == "error"
    assert "DB error" in error["cedar"]["error"]
    
def test_cedar_logger_save_summary(tmp_path: Path) -> None:
    logger: CedarLogger = CedarLogger(tmp_path / "cedar_calls.jsonl")
    logger.record_allow("t1", "tool_a", "assistant", {}, cedar_overhead_ms=10.0)
    logger.record_deny("t1", "tool_b", "assistant", "blocked", cedar_overhead_ms=5.0)
    
    summary_path: Path = logger.save_summary()
    summary = json.loads(summary_path.read_text())
    
    assert summary["total_tool_calls"] == 2
    assert summary["decisions"]["allow"] == 1
    assert summary["decisions"]["deny"] == 1
    assert summary["overhead_ms"]["count"] == 2
    