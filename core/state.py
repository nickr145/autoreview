import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    repo_path: str
    pr_diff: str
    findings: Annotated[list, operator.add]
    patches: Annotated[list, operator.add]
    test_output: str
    test_passed: bool
    iteration: int
    pr_number: int
    repo_slug: str


def initial_state(repo_slug: str, pr_number: int) -> ReviewState:
    return ReviewState(
        repo_path="",
        pr_diff="",
        findings=[],
        patches=[],
        test_output="",
        test_passed=False,
        iteration=0,
        pr_number=pr_number,
        repo_slug=repo_slug,
    )
