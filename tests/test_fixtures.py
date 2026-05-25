"""Accuracy tests: verify Bandit detects known CVE patterns in fixture files.

These run Bandit as a subprocess (no LLM calls) so they are fast and suitable
for CI. The ≥80% recall target is enforced by test_recall_meets_target.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"

FIXTURES = [
    "sql_injection.py",
    "hardcoded_secrets.py",
    "path_traversal.py",
    "insecure_deserialization.py",
    "shell_injection.py",
    "weak_crypto.py",
]


def _run_bandit(path: Path) -> list[dict]:
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "-f", "json", "-l", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(result.stdout).get("results", [])
    except json.JSONDecodeError:
        return []


@pytest.mark.parametrize("filename", FIXTURES)
def test_bandit_detects_vulnerability(filename):
    findings = _run_bandit(FIXTURE_DIR / filename)
    assert len(findings) > 0, f"Bandit found no issues in {filename}"


def test_recall_meets_target():
    """Bandit must flag at least 80% of fixture files (≥5 of 6)."""
    detected = sum(
        1 for f in FIXTURES if _run_bandit(FIXTURE_DIR / f)
    )
    recall = detected / len(FIXTURES)
    assert recall >= 0.8, (
        f"Bandit recall {recall:.0%} is below the 80% target "
        f"({detected}/{len(FIXTURES)} fixtures flagged)"
    )
