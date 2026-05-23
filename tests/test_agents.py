from unittest.mock import MagicMock, patch

import pytest

from core.state import initial_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(**overrides):
    s = initial_state(repo_slug="owner/repo", pr_number=1)
    s.update(overrides)
    return s


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class TestAuditorNode:
    def test_returns_findings_key(self):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state())
        assert "findings" in result

    def test_stub_returns_empty_list(self):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state(pr_diff="--- a/f.py\n+++ b/f.py\n"))
        assert result["findings"] == []


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

class TestQualityNode:
    def test_returns_patches_key(self):
        from agents.quality import quality_node
        result = quality_node(_make_state())
        assert "patches" in result

    def test_stub_returns_empty_list(self):
        from agents.quality import quality_node
        result = quality_node(_make_state(findings=[{"severity": "HIGH"}]))
        assert result["patches"] == []


# ---------------------------------------------------------------------------
# Graph routing
# ---------------------------------------------------------------------------

class TestGraphRouting:
    def test_routes_to_publisher_when_tests_pass(self):
        from core.graph import _route_after_tests
        state = _make_state(test_passed=True, iteration=1)
        assert _route_after_tests(state) == "publisher"

    def test_routes_to_quality_when_tests_fail_and_retries_remain(self):
        from core.graph import _route_after_tests
        state = _make_state(test_passed=False, iteration=1)
        assert _route_after_tests(state) == "quality"

    def test_routes_to_publisher_when_max_iterations_reached(self):
        from core.graph import _route_after_tests
        state = _make_state(test_passed=False, iteration=3)
        assert _route_after_tests(state) == "publisher"
