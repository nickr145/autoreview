import os

from langgraph.graph import END, StateGraph

from agents.auditor import auditor_node
from agents.publisher import publisher_node
from agents.quality import quality_node
from agents.test_runner import test_runner_node
from core.github_client import get_pr_diff
from core.state import ReviewState

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))


def fetcher_node(state: ReviewState) -> dict:
    """Fetch PR diff from GitHub and populate pr_diff in state.

    No-op if pr_diff is already set (allows tests to pre-populate state).
    """
    if state.get("pr_diff"):
        return {}
    try:
        diff = get_pr_diff(state["repo_slug"], state["pr_number"])
        return {"pr_diff": diff}
    except Exception as exc:
        return {"pr_diff": f"# Diff fetch failed: {exc}"}


def _route_after_tests(state: ReviewState) -> str:
    if state["test_passed"] or state["iteration"] >= MAX_ITERATIONS:
        return "publisher"
    return "quality"


def build_graph() -> StateGraph:
    graph = StateGraph(ReviewState)

    graph.add_node("fetcher", fetcher_node)
    graph.add_node("auditor", auditor_node)
    graph.add_node("quality", quality_node)
    graph.add_node("test_runner", test_runner_node)
    graph.add_node("publisher", publisher_node)

    graph.set_entry_point("fetcher")
    graph.add_edge("fetcher", "auditor")
    graph.add_edge("auditor", "quality")
    graph.add_edge("quality", "test_runner")
    graph.add_conditional_edges(
        "test_runner",
        _route_after_tests,
        {"quality": "quality", "publisher": "publisher"},
    )
    graph.add_edge("publisher", END)

    return graph


review_graph = build_graph().compile()
