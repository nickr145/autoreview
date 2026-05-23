from core.state import ReviewState

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


def quality_node(state: ReviewState) -> dict:
    # TODO (S2): call tool_loop with QUALITY_SYSTEM + QUALITY_TOOLS
    # On retries, append state["test_output"] to user prompt for diagnosis
    return {"patches": []}
