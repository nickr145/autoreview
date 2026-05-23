import json
import subprocess


def run_bandit(file_path: str, severity_filter: str = "LOW") -> list[dict]:
    """Run Bandit on file_path, return findings as a list of dicts."""
    level_flag = {"HIGH": "-lll", "MEDIUM": "-ll", "LOW": "-l"}.get(severity_filter, "-l")
    result = subprocess.run(
        ["bandit", "-f", "json", level_flag, file_path],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
        return data.get("results", [])
    except json.JSONDecodeError:
        return []
