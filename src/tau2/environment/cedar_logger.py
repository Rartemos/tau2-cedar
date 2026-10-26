# Author:       Andrew Yohanes (Advisor: Prof. William Eiers)
# Affiliation:  Stevens Institute for Artificial Intelligence (SIAI), Stevens Institute of Technology
# Description:  Cedar tool execution telemetry system for tau2-bench

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


class CedarLogger:
    """Records Cedar access control decisions and tool call diagnostics.
    
    Each record captures one of three possible outcomes:
        - allow: Cedar allowed the tool call to execute.
        - deny: Cedar blocked the call before execution.
        - error: Cedar permitted the call, but tool execution failed.
    
    
            
    Attributes:
        cedar_calls_path: The path for the output Cedar JSONL file.
        summary_path: The path for the Cedar summary JSON file.
    """
    
    def __init__(
        self, 
        cedar_calls_path: Path, 
        summary_path: Path | None = None,
    ) -> None:
        """Initialize the Cedar logger.
        
        Args:
            cedar_calls_path: The file path for ``cedar_calls.jsonl``.
            summary_path: The file path for ``cedar_summary.json``. Defaults to the same directory as ``cedar_calls.json``.
        """
        self.cedar_calls_path = cedar_calls_path
        self.cedar_calls_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.summary_path = (
            Path(summary_path)
            if summary_path is not None
            else self.cedar_calls_path.parent / "cedar_summary.json"
        )
        
        self._call_counter: int = 0
        self._latencies_ms: list[float] = []
        self._decision_counts: dict[str, int] = {
            "allow": 0,
            "deny": 0,
            "error": 0,
        }
        self._policy_hits: dict[str, int] = {}
        self._tool_decisions: dict[str, dict[str, int]] = {}
        self._eval_errors_count: int = 0
    
    def _write(self, event: dict) -> None:
        """Append a single event record to the output JSONL file.
        
        Args:
            event: The event dictionary to append.
        """
        with open(self.cedar_calls_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            
    def _record_stats(
        self,
        decision: Literal["allow", "deny", "error"],
        tool_name: str,
        overhead_ms: float | None,
        policy_ids: list[str] | None,
        eval_errors: list[str] | None,
    ) -> None:
        """Record and update Cedar summary metrics.
        
        Args:
            decision: The Cedar decision of the tool call.
            tool_name: The name of the tool call.
            overhead_ms: The evaluation latency of the tool call in milliseconds.
            policy_ids: Policy IDs that contributed to the decision.
            eval_errors: Diagnostic errors from Cedar.
        """
        self._decision_counts[decision] = self._decision_counts.get(decision, 0) + 1
        
        if overhead_ms is not None:
            self._latencies_ms.append(overhead_ms)
        
        if policy_ids:
            for pid in policy_ids:
                self._policy_hits[pid] = self._policy_hits.get(pid, 0) + 1
        
        if eval_errors:
            self._eval_errors_count += len(eval_errors)
            
        if tool_name not in self._tool_decisions:
            self._tool_decisions[tool_name] = {"allow": 0, "deny": 0, "error": 0}
        self._tool_decisions[tool_name][decision] = (
            self._tool_decisions[tool_name].get(decision, 0) + 1
        )
    
    def record_allow(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        arguments: dict,
        cedar_overhead_ms: float | None = None,
        cedar_policy_ids: list[str] | None = None,       
        cedar_eval_errors: list[str] | None = None,
        cedar_request: dict[str, Any] | None = None,
    ) -> None:
        """Log a tool call that Cedar allowed.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            arguments: The raw tool parameters.
            cedar_overhead_ms: The evaluation latency of the tool call in milliseconds.
            cedar_policy_ids: Policy IDs that allowed the tool call. 
            cedar_eval_errors: Diagnostic errors from Cedar.
            cedar_request: The evaluated Cedar request.
        """
        self._call_counter += 1
        self._record_stats(
            "allow", 
            tool_name,
            cedar_overhead_ms,
            cedar_policy_ids,
            cedar_eval_errors,
        )
        
        self._write({
            "timestamp": _now(),
            "task_id": str(task_id),
            "call_id": self._call_counter,
            "call": {
                "tool": tool_name,
                "requestor": requestor,
                "arguments": arguments,
            },
            "cedar": {
                "decision": "allow",
                "cedar_overhead_ms": cedar_overhead_ms,
                "feedback": None,
                "cedar_policy_ids": cedar_policy_ids or [],            
                "cedar_eval_errors": cedar_eval_errors or [],
                "cedar_request": cedar_request,
            },
        })
        
    def record_deny(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        feedback: str,
        arguments: dict[str, Any] | None = None,
        cedar_overhead_ms: float | None = None,
        cedar_policy_ids: list[str] | None = None,
        cedar_eval_errors: list[str] | None = None,
        cedar_request: dict[str, Any] | None = None,
    ) -> None:
        """Log a tool call that Cedar denied.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            feedback: The natural language feedback for the requestor.
            arguments: The raw tool parameters, if available.
            cedar_overhead_ms: The evaluation latency of the tool call in milliseconds.
            cedar_policy_ids: Policy IDs that denied the tool call. 
            cedar_eval_errors: Diagnostic errors from Cedar.
            cedar_request: The evaluated Cedar request. 
        """
        self._call_counter += 1
        self._record_stats(
            "deny", 
            tool_name,
            cedar_overhead_ms,
            cedar_policy_ids,
            cedar_eval_errors,
        )
        
        self._write({
            "timestamp": _now(),
            "task_id": str(task_id),
            "call_id": self._call_counter,
            "call": {
                "tool": tool_name,
                "requestor": requestor,
                "arguments": arguments or {},
            },
            "cedar": {
                "decision": "deny",
                "cedar_overhead_ms": cedar_overhead_ms,
                "feedback": feedback,
                "cedar_policy_ids": cedar_policy_ids or [],            
                "cedar_eval_errors": cedar_eval_errors or [],
                "cedar_request": cedar_request,
            },
        })
        
    def record_error(
        self, 
        task_id: str, 
        tool_name: str, 
        requestor: str, 
        reason: Exception | str,
        arguments: dict[str, Any] | None = None,
        cedar_overhead_ms: float | None = None,
        cedar_policy_ids: list[str] | None = None,       
        cedar_eval_errors: list[str] | None = None,
        cedar_request: dict[str, Any] | None = None,
    ) -> None:
        """Log a tool call that failed to execute.
        
        Args:
            task_id: The ID of the current task.
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            reason: The exception raised during tool execution.
            arguments: The raw tool parameters, if available.
            cedar_overhead_ms: The evaluation latency of the tool call in milliseconds.
            cedar_policy_ids: Policy IDs that allowed the tool call. 
            cedar_eval_errors: Diagnostic errors from Cedar.
            cedar_request: The evaluated Cedar request.
        """
        self._call_counter += 1
        self._record_stats(
            "error", 
            tool_name,
            cedar_overhead_ms,
            cedar_policy_ids,
            cedar_eval_errors,
        )
        
        self._write({
            "timestamp": _now(),
            "task_id": str(task_id),
            "call_id": self._call_counter,
            "call": {
                "tool": tool_name,
                "requestor": requestor,
                "arguments": arguments or {},
            },
            "cedar": {
                "decision": "error",
                "cedar_overhead_ms": cedar_overhead_ms,
                "feedback": None,
                "error": str(reason),
                "cedar_policy_ids": cedar_policy_ids or [],            
                "cedar_eval_errors": cedar_eval_errors or [],
                "cedar_request": cedar_request,
            },
        })
    
    def get_summary(self) -> dict[str, Any]:
        """Compute summary telemetry metrics and latency distributions.
        
        Returns:
            The dictionary containing overall Cedar metrics.
        """
        total_calls: int = sum(self._decision_counts.values())
        
        if self._latencies_ms:
            sorted_latencies: list[float] = sorted(self._latencies_ms)
            n: int = len(sorted_latencies)
            latency_stats = {
                "count": n,
                "mean_ms": round(statistics.mean(sorted_latencies), 3),
                "median_ms": round(statistics.median(sorted_latencies), 3),
                "p95_ms": round(sorted_latencies[int(n * 0.95)], 3) if n > 1 else round(sorted_latencies[0], 3),
                "p99_ms": round(sorted_latencies[int(n * 0.99)], 3) if n > 1 else round(sorted_latencies[0], 3),
                "min_ms": round(min(sorted_latencies), 3),
                "max_ms": round(max(sorted_latencies), 3),
            }
        else:
            latency_stats = {
                "count": 0,
                "mean_ms": 0.0,
                "median_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
            }
        
        return {
            "generated_at": _now(),
            "total_tool_calls": total_calls,
            "decisions": {
                "allow": self._decision_counts["allow"],
                "deny": self._decision_counts["deny"],
                "error": self._decision_counts["error"],
            },
            "overhead_ms": latency_stats,
            "policy_diagnostics": {
                "policy_hits": self._policy_hits,
                "eval_errors_count": self._eval_errors_count,
            },
            "tool_decisions": self._tool_decisions
        }
        
    def save_summary(self, path: Path | None = None) -> Path:
        """Write summary metrics to the summary JSON file.
        
        Args:
            path: Target file path, or None. If None, defaults to ``self.summary_path``.
        
        Returns:
            The path to the saved summary file.
        """
        target_path: Path = Path(path) if path is not None else self.summary_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        summary: dict[str, Any] = self.get_summary()
        
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return target_path
        

def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()