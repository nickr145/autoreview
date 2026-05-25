import json
import os
import re
import shutil
import subprocess
import tempfile

from core.config import settings
from core.state import ReviewState
from tools.diff_tool import extract_diff_files
from tools.llm_tool import tool_loop
from tools.patch_tool import apply_patch

QUALITY_SYSTEM = """
You are an expert Python/TypeScript engineer conducting a code review.
You will receive a unified diff, a list of security findings, and (on retries)
the previous patch attempt plus the test failure output.

Your task:
  1. Identify PEP 8 / ESLint violations, missing type hints,
     cyclomatic complexity > 10, missing docstrings.
  2. For each security finding, generate a corrective unified diff.
  3. Ensure every diff applies cleanly with `patch -p1`.

Output format:
  { "quality_issues": [...], "patches": ["<unified diff string>", ...] }
"""

QUALITY_TOOLS = [
    {
        "name": "check_complexity",
        "description": "Compute cyclomatic complexity for all functions in a file using radon.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "apply_patch",
        "description": "Apply a unified diff to the scratch volume. Returns success/failure.",
        "input_schema": {
            "type": "object",
            "properties": {"patch_content": {"type": "string"}},
            "required": ["patch_content"],
        },
    },
    {
        "name": "run_linter",
        "description": "Run ruff (Python) or ESLint (TS) and return violations as JSON.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "language": {"type": "string", "enum": ["python", "typescript"]},
            },
            "required": ["file_path", "language"],
        },
    },
]


def _parse_quality_response(raw: str) -> dict:
    """Extract {"quality_issues": [...], "patches": [...]} from Claude's response."""
    for pattern in [r"```(?:json)?\s*(\{.*?\})\s*```", r"(\{.*\})"]:
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    return {}


def quality_node(state: ReviewState) -> dict:
    pr_diff = state.get("pr_diff", "")
    findings = state.get("findings", [])
    iteration = state.get("iteration", 0)
    test_output = state.get("test_output", "")
    prev_patches = state.get("patches", [])

    scratch = extract_diff_files(pr_diff)

    def handle_check_complexity(file_path: str) -> str:
        full = os.path.join(scratch, file_path.lstrip("/"))
        if not os.path.exists(full):
            return f"File not found: {file_path}"
        result = subprocess.run(
            ["radon", "cc", "-s", "-j", full],
            capture_output=True,
            text=True,
        )
        return result.stdout or result.stderr

    def handle_apply_patch(patch_content: str) -> str:
        trial = tempfile.mkdtemp(prefix="autoreview-trial-")
        shutil.copytree(scratch, trial, dirs_exist_ok=True)
        try:
            success, msg = apply_patch(trial, patch_content)
            return f"{'OK' if success else 'FAILED'}: {msg}"
        finally:
            shutil.rmtree(trial, ignore_errors=True)

    def handle_run_linter(file_path: str, language: str) -> str:
        full = os.path.join(scratch, file_path.lstrip("/"))
        if not os.path.exists(full):
            return f"File not found: {file_path}"
        if language == "python":
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", full],
                capture_output=True,
                text=True,
            )
            return result.stdout or "[]"
        return "[]"

    parts = [
        f"PR Diff:\n\n{pr_diff}",
        f"\nSecurity Findings:\n{json.dumps(findings, indent=2)}",
    ]
    if iteration > 0 and test_output:
        parts.append(f"\nPrevious test run FAILED. Output:\n{test_output}")
        if prev_patches:
            parts.append("\nPrevious patches (failed):\n" + "\n---\n".join(prev_patches))

    tracker: list = []
    try:
        raw = tool_loop(
            system=QUALITY_SYSTEM,
            user="\n".join(parts),
            tools=QUALITY_TOOLS,
            tool_handlers={
                "check_complexity": handle_check_complexity,
                "apply_patch": handle_apply_patch,
                "run_linter": handle_run_linter,
            },
            model=settings.claude_quality_model,
            token_tracker=tracker,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    result = _parse_quality_response(raw)
    return {
        "patches": result.get("patches", []),
        "input_tokens": sum(t[0] for t in tracker),
        "output_tokens": sum(t[1] for t in tracker),
    }
