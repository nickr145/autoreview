import os
import tempfile

from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository


def get_client() -> Github:
    return Github(os.environ["GITHUB_TOKEN"])


def get_pr_diff(repo_slug: str, pr_number: int) -> str:
    """Fetch the unified diff for a PR."""
    g = get_client()
    repo = g.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)
    files = pr.get_files()
    chunks = []
    for f in files:
        if f.patch:
            chunks.append(f"--- a/{f.filename}\n+++ b/{f.filename}\n{f.patch}")
    return "\n".join(chunks)


def post_review(
    repo_slug: str,
    pr_number: int,
    body: str,
    comments: list[dict],
) -> None:
    """Post inline review comments + summary body in a single API call."""
    g = get_client()
    repo = g.get_repo(repo_slug)
    pr = repo.get_pull(pr_number)
    pr.create_review(body=body, event="COMMENT", comments=comments)
