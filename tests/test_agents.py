from unittest.mock import patch

import pytest

from core.state import initial_state


def _make_state(**overrides):
    s = initial_state(repo_slug="owner/repo", pr_number=1)
    s.update(overrides)
    return s


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class TestAuditorNode:
    @patch("agents.auditor.tool_loop", return_value="[]")
    def test_returns_findings_key(self, _mock):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state())
        assert "findings" in result

    @patch("agents.auditor.tool_loop", return_value="[]")
    def test_empty_diff_returns_no_findings(self, _mock):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state(pr_diff="--- a/f.py\n+++ b/f.py\n"))
        assert result["findings"] == []

    @patch(
        "agents.auditor.tool_loop",
        return_value='[{"file":"a.py","line":10,"severity":"HIGH","category":"sql","description":"SQL injection","confidence":0.9}]',
    )
    def test_parses_findings_from_json_response(self, _mock):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state(pr_diff="--- a/a.py\n+++ b/a.py\n+x = 1\n"))
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "HIGH"

    @patch(
        "agents.auditor.tool_loop",
        return_value='```json\n[{"file":"b.py","line":5,"severity":"MEDIUM","category":"secrets","description":"Hardcoded password","confidence":0.8}]\n```',
    )
    def test_parses_findings_from_markdown_code_block(self, _mock):
        from agents.auditor import auditor_node
        result = auditor_node(_make_state(pr_diff="--- a/b.py\n+++ b/b.py\n+pw = 'secret'\n"))
        assert len(result["findings"]) == 1
        assert result["findings"][0]["category"] == "secrets"


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

class TestQualityNode:
    @patch("agents.quality.tool_loop", return_value='{"patches": []}')
    def test_returns_patches_key(self, _mock):
        from agents.quality import quality_node
        result = quality_node(_make_state())
        assert "patches" in result

    @patch("agents.quality.tool_loop", return_value='{"patches": []}')
    def test_empty_findings_returns_empty_patches(self, _mock):
        from agents.quality import quality_node
        result = quality_node(_make_state(findings=[{"severity": "HIGH"}]))
        assert result["patches"] == []

    @patch(
        "agents.quality.tool_loop",
        return_value='{"quality_issues": [], "patches": ["--- a/x.py\\n+++ b/x.py\\n@@ -1 +1 @@\\n-bad\\n+good\\n"]}',
    )
    def test_parses_patches_from_response(self, _mock):
        from agents.quality import quality_node
        result = quality_node(_make_state(findings=[{"severity": "HIGH"}]))
        assert len(result["patches"]) == 1
        assert "--- a/x.py" in result["patches"][0]

    @patch("agents.quality.tool_loop", return_value='{"patches": ["patch1", "patch2"]}')
    def test_includes_retry_context_when_iteration_gt_zero(self, mock_tl):
        from agents.quality import quality_node
        quality_node(_make_state(iteration=1, test_output="FAILED: assertion error", patches=["old patch"]))
        call_kwargs = mock_tl.call_args
        user_prompt = call_kwargs[1]["user"] if call_kwargs[1] else call_kwargs[0][1]
        assert "FAILED" in user_prompt
        assert "old patch" in user_prompt


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
