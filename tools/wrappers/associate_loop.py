import json
import os
import subprocess
import sys
import time
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Add the repo root to path so we can import from supervisor
sys.path.append(str(Path(__file__).resolve().parents[2]))

def load_task(task_path: str) -> Dict[str, Any]:
    with open(task_path, 'r') as f:
        if task_path.endswith('.yaml') or task_path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def setup_sandbox(task: Dict[str, Any]):
    print(f"Setting up sandbox for task {task['id']}...")
    # Checkout branch, install deps, etc.
    # In a real implementation, this would handle git worktrees.

def run_agent(task: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Running Associate Agent for task {task['id']}...")
    # This is a stub for the actual agent invocation.
    # In the "Human-as-Director" bootstrapping phase, this might just check if
    # the user has done the work, or it might run a simple script.
    # For now, we assume the work is done *before* this script is called,
    # or that this script is just verifying.

    # Future: Call AgentHarness here.

    return {
        "status": "success",
        "decision": "propose_done",
        "summary": "Executed task loop.",
        "artifacts": {}
    }

def verify_work(task: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("Verifying work...")
    results = []
    for cmd in task.get('verification_commands', []):
        print(f"Running check: {cmd}")
        try:
            # Security Note: shell=True is dangerous with untrusted input.
            # In Phase 3, we rely on the sandbox isolation (Ralph-in-Ralph).
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=task.get('time_budget_s', 300)
            )

            output_snippet = result.stdout + "\n" + result.stderr
            # Truncate if too long
            if len(output_snippet) > 1000:
                output_snippet = output_snippet[:1000] + "...[truncated]"

            results.append({
                "command": cmd,
                "exit_code": result.returncode,
                "output_snippet": output_snippet
            })
        except Exception as e:
            results.append({
                "command": cmd,
                "exit_code": -1,
                "output_snippet": f"Execution failed: {str(e)}"
            })

    return results

def write_evidence(task: Dict[str, Any], agent_result: Dict[str, Any], verification_results: List[Dict[str, Any]]):
    run_id = f"run-{int(time.time())}"
    evidence_dir = Path(f"evidence/{task['id']}/{run_id}")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Ensure logs dir exists if we use it
    (evidence_dir / "checks").mkdir(exist_ok=True)

    # Write detailed logs for checks
    for i, res in enumerate(verification_results):
        log_path = evidence_dir / "checks" / f"check_{i}.log"
        with open(log_path, "w") as f:
            f.write(f"Command: {res['command']}\n")
            f.write(f"Exit Code: {res['exit_code']}\n")
            f.write("-" * 20 + "\n")
            f.write(res['output_snippet'])

    manifest = {
        "run_id": run_id,
        "task_id": task['id'],
        "status": agent_result['status'],
        "decision": agent_result['decision'],
        "summary": agent_result.get('summary', ''),
        "checks": verification_results,
        "provenance": {
            "timestamp": time.ctime(),
            "git_commit": "HEAD" # Should fetch actual commit
        }
    }

    with open(evidence_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Evidence written to {evidence_dir}")

def main():
    parser = argparse.ArgumentParser(description="Associate Loop Wrapper")
    parser.add_argument("--task", required=True, help="Path to task YAML/JSON")
    args = parser.parse_args()

    try:
        task = load_task(args.task)
    except FileNotFoundError:
        print(f"Error: Task file not found: {args.task}")
        sys.exit(1)

    setup_sandbox(task)
    agent_result = run_agent(task, {})
    verification_results = verify_work(task)
    write_evidence(task, agent_result, verification_results)

if __name__ == "__main__":
    main()
