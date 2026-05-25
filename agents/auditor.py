import json
import os
import re
import shutil

from core.config import settings
from core.state import ReviewState
from tools.bandit_tool import run_bandit
from tools.diff_tool import extract_diff_files
from tools.llm_tool import tool_loop

AUDITOR_SYSTEM = """
You are a security-focused code auditor. You will receive:
  1. A unified diff of a pull request.
  2. JSON output from Bandit static analysis.

Respond ONLY with a JSON array of findings. Each finding:
  { "file": str, "line": int, "severity": "HIGH|MEDIUM|LOW",
    "category": str, "description": str, "confidence": float }

Flag: SQL injection, hardcoded secrets, path traversal,
      insecure deserialization, use of eval/exec.
Do NOT include low-confidence (< 0.4) findings.
"""

AUDITOR_TOOLS = [
    {
        "name": "run_bandit_scan",
        "description": "Run Bandit static analysis on a file inside the Docker sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "severity_filter": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "read_file_chunk",
        "description": "Read a slice of a file for additional context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["file_path", "start_line", "end_line"],
        },
    },
]


def _parse_findings(raw: str) -> list[dict]:
    """Extract a JSON array from Claude's text response."""
    for pattern in [r"```(?:json)?\s*(\[.*?\])\s*```", r"(\[.*\])"]:
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
    try:
        data = json.loads(raw.strip())
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def auditor_node(state: ReviewState) -> dict:
    pr_diff = state.get("pr_diff", "")
    scratch = extract_diff_files(pr_diff)

    def handle_run_bandit_scan(file_path: str, severity_filter: str = "LOW") -> str:
        full = os.path.join(scratch, file_path.lstrip("/"))
        if not os.path.exists(full):
            return f"File not found in diff: {file_path}"
        findings = run_bandit(full, severity_filter)
        return json.dumps(findings)

    def handle_read_file_chunk(file_path: str, start_line: int, end_line: int) -> str:
        full = os.path.join(scratch, file_path.lstrip("/"))
        try:
            with open(full) as fh:
                lines = fh.readlines()
            return "".join(lines[max(0, start_line - 1) : end_line])
        except FileNotFoundError:
            return f"File not found: {file_path}"

    tracker: list = []
    try:
        raw = tool_loop(
            system=AUDITOR_SYSTEM,
            user=f"PR Diff:\n\n{pr_diff}",
            tools=AUDITOR_TOOLS,
            tool_handlers={
                "run_bandit_scan": handle_run_bandit_scan,
                "read_file_chunk": handle_read_file_chunk,
            },
            model=settings.claude_auditor_model,
            thinking=settings.thinking_enabled,
            token_tracker=tracker,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return {
        "findings": _parse_findings(raw),
        "input_tokens": sum(t[0] for t in tracker),
        "output_tokens": sum(t[1] for t in tracker),
    }
