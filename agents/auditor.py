from core.state import ReviewState

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


def auditor_node(state: ReviewState) -> dict:
    # TODO (S2): call tool_loop with AUDITOR_SYSTEM + AUDITOR_TOOLS + extended thinking
    return {"findings": []}
