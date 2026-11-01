import argparse
import json

from pathlib import Path
from typing import Any

from tau2.data_model.simulation import Results
from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment
from tau2.registry import registry
from tau2.run import get_tasks


def load_simulation_data(sim_dir: Path) -> tuple[Results | None, list[dict]]:
    """Load results.json and/or cedar_calls.jsonl from simulation directory."""
    results_path: Path = sim_dir / "results.json"
    cedar_calls_path: Path = sim_dir / "cedar_calls.jsonl"
    
    results: Results | None = None
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            results = Results.model_validate_json(f.read())
            
    cedar_calls: list[dict] = []
    if cedar_calls_path.exists():
        with open(cedar_calls_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cedar_calls.append(json.loads(line))
                    
    return results, cedar_calls

def build_ground_truth_environment(domain: str, task: Task) -> Environment:
    """Build a new ground-truth environment initialized to the task's starting state."""
    env_constructor = registry.get_env_constructor(domain)
    env = env_constructor() # Instantiate environment without Cedar authorizer
    
    # Apply task initial state
    if task.initial_state is not None:
        env.set_state(
            initialization_data=task.initial_state.initialization_data,
            initialization_actions=task.initial_state.initialization_actions,
            message_history=task.initial_state.message_history or [],
        )
    return env

def test_tool_against_ground_truth(
    ground_truth_env: Environment,
    tool_name: str,
    arguments: dict[str, Any],
) -> bool:
    """Execute tool against the unmonitored ground-truth domain toolkit."""
    if ground_truth_env.tools is not None and ground_truth_env.tools.has_tool(tool_name):
        try:
            ground_truth_env.tools.use_tool(tool_name=tool_name, **arguments)
            return True
        except Exception:
            return False
    elif ground_truth_env.user_tools is not None and ground_truth_env.user_tools.has_tool(tool_name):
        try:
            ground_truth_env.user_tools.use_tool(tool_name=tool_name, **arguments)
            return True
        except Exception:
            return False
    else:
        return False # Hallucinated or tool name doesn't exist

def evaluate_confusion_matrix(
    sim_dir: Path, 
    domain: str | None = None,
    output_json: Path | None = None,
) -> dict[str, Any]:
    """Calculate the confusion matrix comparing Cedar against domain ground truth."""
    results, cedar_calls = load_simulation_data(sim_dir)
    
    # Determine domain
    if domain is None:
        if results and hasattr(results.info, "environment_info"):
            domain = results.info.environment_info.domain_name
        else:
            raise ValueError(
                "Domain could not be determined from results.json. "
                "Please specify --domain explicitly"
            )
    
    print(f"\n[INFO] Loading tasks and building ground-truth environments for: '{domain}'...")
    tasks: list[Task] = get_tasks(domain)
    task_map: dict[str, Task] = {str(t.id): t for t in tasks}
    
    # Tracking matrix counts
    # Positive = Allow, Negative = Deny
    # TP: Cedar Allow, Ground-Truth Allow (Correctly allowed)
    # FP: Cedar Allow, Ground-Truth Deny (Incorrectly allowed, overly permissive)
    # TN: Cedar Deny, Ground-Truth Deny (Correctly denied)
    # FN: Cedar Deny, Ground-Truth Allow (Incorrectly denied, overly restrictive)
    counts: dict[str, int] = {
        "TP": 0,
        "FP": 0,
        "TN": 0,
        "FN": 0,
        "total_calls": 0,
    }
    
    tool_decisions: dict[str, dict[str, int]] = {}
    
    def update_counts(tool_name: str, cedar_allowed: bool, ground_truth_allowed: bool):
        counts["total_calls"] += 1
        if tool_name not in tool_decisions:
            tool_decisions[tool_name] = {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
        
        # Compare Cedar decision against ground truth
        if cedar_allowed and ground_truth_allowed:
            counts["TP"] += 1
            tool_decisions[tool_name]["TP"] += 1
        elif cedar_allowed and not ground_truth_allowed:
            counts["FP"] += 1
            tool_decisions[tool_name]["FP"] += 1
        elif not cedar_allowed and not ground_truth_allowed:
            counts["TN"] += 1
            tool_decisions[tool_name]["TN"] += 1
        else:
            counts["FN"] += 1
            tool_decisions[tool_name]["FN"] += 1
    
    # Stream through cedar_calls.jsonl grouped by task
    if cedar_calls:
        print(f"[INFO] Evaluating {len(cedar_calls)} calls recorded in 'cedar_calls.jsonl'...")
    
        # Group calls by task to preserve state progression within each task
        calls_by_task: list[dict[str, Any]] = {}
        for call in cedar_calls:
            calls_by_task.setdefault(str(call.get("task_id", "")), []).append(call)
            
        for task_id, task_calls in calls_by_task.items():
            task = task_map.get(task_id)
            if not task:
                continue
            
            ground_truth_env: Environment = build_ground_truth_environment(domain, task)
            
            for call_event in task_calls:
                call_info = call_event.get("call", {})
                cedar_info = call_event.get("cedar", {})
                
                tool_name = call_info.get("tool", "")
                arguments = call_info.get("arguments", {})
                cedar_decision = cedar_info.get("decision", "allow")
                cedar_allowed = (cedar_decision == "allow")
                
                # Test ground truth against domain toolkit
                ground_truth_allowed: bool = test_tool_against_ground_truth(ground_truth_env, tool_name, arguments)
                update_counts(tool_name, cedar_allowed, ground_truth_allowed)
    
    # Fallback to results.json trajectory messages
    elif results and results.simulations:
        print(f"[INFO] Evaluating {len(results.simulations)} simulation trajectories...")
        for sim in results.simulations:
            task_id = str(sim.task_id)
            task = task_map.get(task_id)
            if not task or not sim.messages:
                continue
            
            ground_truth_env: Environment = build_ground_truth_environment(domain, task)
            
            for msg in sim.messages:
                if msg.role == "assistant" and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.name
                        arguments = tool_call.arguments or {}
                        cedar_allowed = True
                        
                        ground_truth_allowed = test_tool_against_ground_truth(ground_truth_env, tool_name, arguments)
                        update_counts(tool_name, cedar_allowed, ground_truth_allowed)
                
    tp: int = counts["TP"]
    fp: int = counts["FP"]
    tn: int = counts["TN"]
    fn: int = counts["FN"]
    total: int = counts["total_calls"]
    
    accuracy: float = (tp + tn) / total if total > 0 else 0.0           # What percentage of decisions were correct? (Correct / Total)
    allow_precision: float = tp / (tp + fp) if (tp + fp) > 0 else 0.0   # When Allow, how often is it correct? (Valid Allows / All Allows)
    deny_precision: float = tn / (tn + fn) if (tn + fn) > 0 else 0.0    # When Deny, how often is it correct? (Valid Blocks / All Blocks)
    allow_recall: float = tp / (tp + fn) if (tp + fn) > 0 else 0.0      # How many valid actions were allowed (Allowed Actions / All Allowed Actions)
    deny_recall: float = tn / (tn + fp) if (tn + fp) > 0 else 0.0       # How many unauthorized actions were blocked (Blocked Actions / All Blocked Actions)
    
    # Harmonic mean of precision and recall
    allow_f1_score: float = (
        2 * (allow_precision * allow_recall) / (allow_precision + allow_recall) 
        if (allow_precision + allow_recall) > 0 else 0.0
    )
    
    deny_f1_score: float = (
        2 * (deny_precision * deny_recall) / (deny_precision + deny_recall) 
        if (deny_precision + deny_recall) > 0 else 0.0
    )
    
    # Build JSON summary
    confusion_matrix_summary = {
        "domain": domain,
        "total_tool_calls": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "allow": {
            "precision": round(allow_precision, 4),
            "recall": round(allow_recall, 4),
            "f1_score": round(allow_f1_score, 4),
        },
        "deny": {
            "precision": round(deny_precision, 4),
            "recall": round(deny_recall, 4),
            "f1_score": round(deny_f1_score, 4),
        },
        "tool_decisions": tool_decisions,
    }
    
    # Print summary
    print("\n" + "=" * 65)
    print(f"       CEDAR CONFUSION MATRIX: {domain.upper()}")
    print("=" * 65)
    print(f"  TP (Allowed Valid)  : {tp}")
    print(f"  FP (Allowed Invalid): {fp}")
    print(f"  TN (Blocked Invalid): {tn}")
    print(f"  FN (Blocked Valid)  : {fn}")
    print(f"  Total Calls         : {total}")
    print(f"  Accuracy            : {accuracy:.4%}")
    print("-" * 65)
    print("F1 Score: ALLOW")
    print(
        f"  Precision: {allow_precision:.4f} | "
        f"Recall: {allow_recall:.4f} | "
        f"F1: {allow_f1_score:.4f}"
    )
    print("-" * 65)
    print("F1 Score: DENY")
    print(
        f"  Precision: {deny_precision:.4f} | "
        f"Recall: {deny_recall:.4f} | "
        f"F1: {deny_f1_score:.4f}"
    )
    print("=" * 65 + "\n")
    
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(confusion_matrix_summary, f, indent=2)
        print(f"[INFO] Detailed metrics saved to: {output_json}")
        
    return confusion_matrix_summary
    
def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Cedar Authorization Confusion Matrix against Ground Truth."
    )
    parser.add_argument(
        "--sim-dir",
        type=Path,
        required=True,
        help="Path to the simulation results directory.",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Domain name. If omitted, inferred from results.json.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to save the output JSON metrics file.",
    )
    args = parser.parse_args()
    evaluate_confusion_matrix(
        sim_dir=args.sim_dir,
        domain=args.domain,
        output_json=args.output_json,
    )

if __name__ == "__main__":
    main()