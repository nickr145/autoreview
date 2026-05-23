from core.sandbox import clone_to_scratch, run_in_sandbox
from core.state import ReviewState
from tools.patch_tool import apply_patch


def test_runner_node(state: ReviewState) -> dict:
    # TODO (S3): apply patches to scratch, run pytest/Jest, capture result
    scratch = clone_to_scratch(state["repo_path"]) if state["repo_path"] else "/tmp/empty"

    for patch in state["patches"]:
        success, msg = apply_patch(scratch, patch)
        if not success:
            return {
                "test_output": f"Patch application failed: {msg}",
                "test_passed": False,
                "iteration": state["iteration"] + 1,
            }

    exit_code, output = run_in_sandbox(
        cmd=["pytest", "--tb=short", "-q"],
        repo_path=scratch,
        writable=True,
    )

    return {
        "test_output": output,
        "test_passed": exit_code == 0,
        "iteration": state["iteration"] + 1,
    }
