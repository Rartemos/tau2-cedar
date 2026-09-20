import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class ToolLogger:
    """Records tool call outcomes to a structured JSONL file.
    
    Tracks three distinct statuses per invocation:
        - success: Cedar permitted the call and it executed without error.
        - cedar_denied: Cedar explicitly blocked the call.
        - error: Cedar permitted the call but it failed during execution.
            
    Attributes:
        output_path (Path): Path to the output JSONL file.
    """
    
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _write(self, event: dict) -> None:
        """Append a single event record to the output file.
        
        Args:
            event (dict): The event data to serialize and write.
        """
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        
    def log_success(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        arguments: dict,
        cedar_request: Optional[dict[str, Any]] = None,
        cedar_overhead_ms: Optional[float] = None,
        cedar_policy_ids: Optional[list[str]] = None,       
        cedar_eval_errors: Optional[list[str]] = None,
    ) -> None:
        """Log a successful tool call.
        
        Args:
            task_id (str): The ID of the current simulation task.
            tool_name (str): The name of the tool that was called.
            requestor (str): The identity of the caller (e.g., "assistant" or "user").
            arguments (dict): The arguments passed to the tool.
            cedar_request (dict[str, Any], optional): The full Cedar authorization request dictionary. Defaults to None.
            cedar_policy_ids (list[str], optional): The Cedar policy IDs that triggered the denial. Defaults to None.
            cedar_eval_errors (list[str], optional): Any errors raised by the Cedar evaluation engine. Defaults to None.
        """
        self._write({
            "timestamp": _now(),
            "task_id": task_id,
            "status": "success",
            "cedar_overhead_ms": cedar_overhead_ms,
            "tool": tool_name,
            "requestor": requestor,
            "arguments": arguments,
            "cedar_request": cedar_request,
            "cedar_policy_ids": cedar_policy_ids,            
            "cedar_eval_errors": cedar_eval_errors,
        })
        
    def log_cedar_denied(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        reason: str,
        cedar_request: Optional[dict[str, Any]] = None,
        cedar_overhead_ms: Optional[float] = None,
        cedar_policy_ids: Optional[list[str]] = None,       
        cedar_eval_errors: Optional[list[str]] = None,
    ) -> None:
        """Log a tool call blocked by Cedar.
        
        Args:
            task_id (str): The ID of the current simulation task.
            tool_name (str): The name of the tool that was denied.
            requestor (str): The identity of the caller (e.g., "assistant" or "user").
            reason (str): The Cedar policy feedback message explaining the denial.
            cedar_request (dict[str, Any], optional): The full Cedar authorization request dictionary. Defaults to None.
            cedar_policy_ids (list[str], optional): The Cedar policy IDs that triggered the denial. Defaults to None.
            cedar_eval_errors (list[str], optional): Any errors raised by the Cedar evaluation engine. Defaults to None.
        """
        self._write({
            "timestamp": _now(),
            "task_id": task_id,
            "status": "denied",
            "cedar_overhead_ms": cedar_overhead_ms,
            "tool": tool_name,
            "requestor": requestor,
            "reason": reason,
            "cedar_request": cedar_request,
            "cedar_policy_ids": cedar_policy_ids,            
            "cedar_eval_errors": cedar_eval_errors,
        })
        
    def log_error(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        error: Exception,
        cedar_request: Optional[dict[str, Any]] = None,
        cedar_overhead_ms: Optional[float] = None,
        cedar_policy_ids: Optional[list[str]] = None,       
        cedar_eval_errors: Optional[list[str]] = None,
    ) -> None:
        """Log a tool call that failed during execution.
        
        Cedar was not involved; the tool was authorized but raised an exception.
        
        Args:
            task_id (str): The ID of the current simulation task.
            tool_name (str): The name of the tool that failed.
            requestor (str): The identity of the caller (e.g., "assistant" or "user").
            error (Exception): The exception raised during tool execution.
            cedar_request (dict[str, Any], optional): The full Cedar authorization request dictionary. Defaults to None.
            cedar_policy_ids (list[str], optional): The Cedar policy IDs that triggered the denial. Defaults to None.
            cedar_eval_errors (list[str], optional): Any errors raised by the Cedar evaluation engine. Defaults to None.
        """
        self._write({
            "timestamp": _now(),
            "task_id": task_id,
            "status": "failed",
            "cedar_overhead_ms": cedar_overhead_ms,
            "tool": tool_name,
            "requestor": requestor,
            "error": str(error),
            "cedar_request": cedar_request,
            "cedar_policy_ids": cedar_policy_ids,            
            "cedar_eval_errors": cedar_eval_errors,
        })
        

def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()