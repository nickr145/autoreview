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
# Test Runner
# ---------------------------------------------------------------------------

_PY_DIFF = "--- a/x.py\n+++ b/x.py\n+print('hello')\n"


class TestTestRunnerNode:
    @patch("agents.test_runner.run_in_sandbox", return_value=(0, "OK"))
    def test_returns_required_keys(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF))
        assert "test_output" in result
        assert "test_passed" in result
        assert "iteration" in result

    @patch("agents.test_runner.run_in_sandbox", return_value=(0, "OK"))
    def test_iteration_increments(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF, iteration=1))
        assert result["iteration"] == 2

    @patch("agents.test_runner.run_in_sandbox", return_value=(0, "OK"))
    def test_passes_when_sandbox_exits_zero(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF))
        assert result["test_passed"] is True

    @patch("agents.test_runner.run_in_sandbox", return_value=(1, "SyntaxError"))
    def test_fails_when_syntax_check_fails(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF))
        assert result["test_passed"] is False

    @patch("agents.test_runner.run_in_sandbox", return_value=(0, '{"results": [{"issue_severity": "HIGH"}], "metrics": {}}'))
    def test_fails_when_bandit_finds_high_severity(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF))
        assert result["test_passed"] is False

    @patch("agents.test_runner.apply_patch", return_value=(False, "hunk mismatch"))
    def test_patch_failure_short_circuits(self, _mock):
        from agents.test_runner import test_runner_node
        result = test_runner_node(_make_state(pr_diff=_PY_DIFF, patches=["bad patch"]))
        assert result["test_passed"] is False
        assert "Patch application failed" in result["test_output"]

    def test_no_python_files_passes_trivially(self):
        from agents.test_runner import test_runner_node
        # Diff with only a non-Python file — sandbox never called
        diff = "--- a/README.md\n+++ b/README.md\n+# hello\n"
        result = test_runner_node(_make_state(pr_diff=diff))
        assert result["test_passed"] is True


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------

class TestFetcherNode:
    def test_noop_when_pr_diff_already_set(self):
        from core.graph import fetcher_node
        result = fetcher_node(_make_state(pr_diff="existing diff"))
        assert result == {}

    @patch("core.graph.get_pr_diff", return_value="fetched diff")
    def test_fetches_diff_when_empty(self, _mock):
        from core.graph import fetcher_node
        result = fetcher_node(_make_state())
        assert result["pr_diff"] == "fetched diff"

    @patch("core.graph.get_pr_diff", side_effect=Exception("no token"))
    def test_graceful_failure_on_github_error(self, _mock):
        from core.graph import fetcher_node
        result = fetcher_node(_make_state())
        assert "Diff fetch failed" in result["pr_diff"]


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

class TestPublisherNode:
    @patch("agents.publisher.post_review")
    def test_calls_post_review_when_repo_and_pr_set(self, mock_post):
        from agents.publisher import publisher_node
        state = _make_state(
            repo_slug="owner/repo",
            pr_number=42,
            findings=[{"file": "a.py", "line": 10, "severity": "HIGH", "description": "SQL injection", "confidence": 0.9}],
        )
        publisher_node(state)
        mock_post.assert_called_once()

    @patch("agents.publisher.post_review")
    def test_skips_post_review_when_repo_slug_empty(self, mock_post):
        from agents.publisher import publisher_node
        state = _make_state(repo_slug="", pr_number=0)
        publisher_node(state)
        mock_post.assert_not_called()

    def test_summary_includes_cost(self):
        from agents.publisher import _build_summary
        state = _make_state(
            findings=[{"severity": "HIGH"}],
            patches=["p1"],
            test_passed=True,
            iteration=1,
            input_tokens=100_000,
            output_tokens=20_000,
        )
        summary = _build_summary(state)
        assert "100,000" in summary
        assert "Est. cost" in summary

    def test_summary_counts_severities(self):
        from agents.publisher import _build_summary
        state = _make_state(findings=[
            {"severity": "HIGH"},
            {"severity": "HIGH"},
            {"severity": "MEDIUM"},
        ])
        summary = _build_summary(state)
        assert "HIGH: 2" in summary
        assert "MEDIUM: 1" in summary

    def test_auditor_returns_token_keys(self):
        """Auditor node must return input_tokens and output_tokens for state accumulation."""
        with patch("agents.auditor.tool_loop", return_value="[]"):
            from agents.auditor import auditor_node
            result = auditor_node(_make_state())
            assert "input_tokens" in result
            assert "output_tokens" in result

    def test_quality_returns_token_keys(self):
        """Quality node must return input_tokens and output_tokens for state accumulation."""
        with patch("agents.quality.tool_loop", return_value='{"patches": []}'):
            from agents.quality import quality_node
            result = quality_node(_make_state())
            assert "input_tokens" in result
            assert "output_tokens" in result


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
