import json
import os
import shutil

from core.sandbox import run_in_sandbox
from core.state import ReviewState
from tools.diff_tool import extract_diff_files
from tools.patch_tool import apply_patch


def _collect_python_files(base: str) -> list[str]:
    """Return relative paths of all .py files under base."""
    result = []
    for root, _, files in os.walk(base):
        for fname in files:
            if fname.endswith(".py"):
                result.append(os.path.relpath(os.path.join(root, fname), base))
    return result


def _has_high_severity(bandit_output: str) -> bool:
    """Return True if bandit JSON output contains any HIGH severity finding."""
    try:
        data = json.loads(bandit_output)
        return any(r.get("issue_severity") == "HIGH" for r in data.get("results", []))
    except json.JSONDecodeError:
        return False


def test_runner_node(state: ReviewState) -> dict:
    pr_diff = state.get("pr_diff", "")
    patches = state.get("patches", [])
    iteration = state.get("iteration", 0)

    scratch = extract_diff_files(pr_diff)

    try:
        for patch in patches:
            success, msg = apply_patch(scratch, patch)
            if not success:
                return {
                    "test_output": f"Patch application failed:\n{msg}",
                    "test_passed": False,
                    "iteration": iteration + 1,
                }

        py_files = _collect_python_files(scratch)
        if not py_files:
            return {
                "test_output": "No Python files in diff — skipping sandbox validation.",
                "test_passed": True,
                "iteration": iteration + 1,
            }

        # Sandbox paths are relative to the /sandbox mount point
        sandbox_paths = [f"/sandbox/{f}" for f in py_files]
        output_parts: list[str] = []
        syntax_ok = True
        bandit_ok = True

        # 1. Syntax check
        exit_code, out = run_in_sandbox(
            cmd=["python", "-m", "py_compile"] + sandbox_paths,
            repo_path=scratch,
        )
        output_parts.append(f"=== Syntax ===\n{out.strip() or 'OK'}")
        if exit_code != 0:
            syntax_ok = False

        # 2. Bandit security scan — fail only on HIGH severity
        exit_code, out = run_in_sandbox(
            cmd=["bandit", "-f", "json", "-l"] + sandbox_paths,
            repo_path=scratch,
        )
        output_parts.append(f"=== Bandit ===\n{out.strip()}")
        if _has_high_severity(out):
            bandit_ok = False

        # 3. Ruff lint — included in output but not a hard gate
        _exit_code, out = run_in_sandbox(
            cmd=["ruff", "check"] + sandbox_paths,
            repo_path=scratch,
        )
        output_parts.append(f"=== Ruff ===\n{out.strip() or 'OK'}")

        return {
            "test_output": "\n\n".join(output_parts),
            "test_passed": syntax_ok and bandit_ok,
            "iteration": iteration + 1,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
