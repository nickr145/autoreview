import subprocess


def apply_patch(repo_path: str, patch_content: str) -> tuple[bool, str]:
    """Apply a unified diff to repo_path.

    Dry-runs first to validate syntax, then applies for real.
    Returns (success, output_message).
    """
    dry = subprocess.run(
        ["patch", "-p1", "--dry-run"],
        input=patch_content,
        text=True,
        capture_output=True,
        cwd=repo_path,
    )
    if dry.returncode != 0:
        return False, f"Patch validation failed:\n{dry.stderr}"

    result = subprocess.run(
        ["patch", "-p1"],
        input=patch_content,
        text=True,
        capture_output=True,
        cwd=repo_path,
    )
    return result.returncode == 0, result.stdout + result.stderr
