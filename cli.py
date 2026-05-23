import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(help="AutoReview Agent — autonomous AI code review")


@app.command()
def run(
    repo: str = typer.Option(..., help="GitHub repo slug, e.g. owner/repo"),
    pr: int = typer.Option(..., help="Pull request number"),
) -> None:
    """Run a full AutoReview pass on a GitHub PR."""
    import weave

    from core.graph import review_graph
    from core.state import initial_state

    weave.init("autoreview-agent")

    typer.echo(f"Starting review: {repo} PR#{pr}")
    state = initial_state(repo_slug=repo, pr_number=pr)
    result = review_graph.invoke(state)

    findings = result.get("findings", [])
    patches = result.get("patches", [])
    passed = result.get("test_passed", False)
    iterations = result.get("iteration", 0)

    typer.echo(f"Findings : {len(findings)}")
    typer.echo(f"Patches  : {len(patches)}")
    typer.echo(f"Tests    : {'PASSED' if passed else 'FAILED'} ({iterations} iteration(s))")


if __name__ == "__main__":
    app()
