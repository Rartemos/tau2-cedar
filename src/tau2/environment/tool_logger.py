# Author:       Andrew Yohanes (Advisor: Prof. William Eiers)
# Affiliation:  Stevens Institute for Artificial Intelligence (SIAI), Stevens Institute of Technology
# Description:  Cedar tool execution telemetry system for tau2-bench

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ToolLogger:
    """Records tool call results and diagnostics.
    
    Each record captures one of three possible outcomes:
        - success: Cedar permitted the call and it executed without error.
        - denied: Cedar blocked the call before execution.
        - failed: Cedar permitted the call but execution failed.
            
    Attributes:
        output_path: Path to the output JSONL file.
    """
    
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _write(self, event: dict) -> None:
        """Append a single event record to the output JSONL file.
        
        Args:
            event: The event dictionary to append.
        """
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    
    def record_success(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        arguments: dict,
        cedar_overhead_ms: float | None = None,
        cedar_request: dict[str, Any] | None = None,
        cedar_policy_ids: list[str] | None = None,       
        cedar_eval_errors: list[str] | None = None,
    ) -> None:
        """Log a successful tool call.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            arguments: The raw tool parameters.
            cedar_overhead_ms: Evaluation latency in milliseconds.
            cedar_request: The structured request evaluated by Cedar.
            cedar_policy_ids: Policy IDs that permitted the tool call. 
            cedar_eval_errors: Diagnostic errors from the Cedar engine.
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
        
    def record_denial(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        reason: str,
        cedar_overhead_ms: float | None = None,
        cedar_request: dict[str, Any] | None = None,
        cedar_policy_ids: list[str] | None = None,       
        cedar_eval_errors: list[str] | None = None,
    ) -> None:
        """Log a tool call that was blocked by Cedar.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            reason: The natural language feedback for the requestor.
            cedar_overhead_ms: Evaluation latency in milliseconds.
            cedar_request: The structured request evaluated by Cedar. 
            cedar_policy_ids: Policy IDs that denied the tool call. 
            cedar_eval_errors: Diagnostic errors from the Cedar engine.
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
        
    def record_failure(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        reason: Exception,
        cedar_overhead_ms: float | None = None,
        cedar_request: dict[str, Any] | None = None,
        cedar_policy_ids: list[str] | None = None,       
        cedar_eval_errors: list[str] | None = None,
    ) -> None:
        """Log a tool call that was allowed by Cedar, but failed during execution.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            reason: The exception raised during tool execution.
            cedar_overhead_ms: Evaluation latency in milliseconds.
            cedar_request: The structured request evaluated by Cedar. 
            cedar_policy_ids: Policy IDs that permitted the tool call. 
            cedar_eval_errors: Diagnostic errors from the Cedar engine.
        """
        self._write({
            "timestamp": _now(),
            "task_id": task_id,
            "status": "failed",
            "cedar_overhead_ms": cedar_overhead_ms,
            "tool": tool_name,
            "requestor": requestor,
            "error": str(reason),
            "cedar_request": cedar_request,
            "cedar_policy_ids": cedar_policy_ids,            
            "cedar_eval_errors": cedar_eval_errors,
        })
        

def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()