# Run Review

Invoke the AutoReview agent against a real GitHub PR via the CLI. Requires ANTHROPIC_API_KEY, GITHUB_TOKEN, and WANDB_API_KEY to be set in .env.

## Usage

```bash
uv run python cli.py run --repo <owner/repo> --pr <pr-number>
```

## Steps

1. Check that required env vars are present (do not print their values):
```bash
uv run python -c "import os; missing = [k for k in ['ANTHROPIC_API_KEY','GITHUB_TOKEN','WANDB_API_KEY'] if not os.getenv(k)]; print('Missing:', missing) if missing else print('All env vars present')"
```

2. Run the review:
```bash
uv run python cli.py run --repo $REPO --pr $PR_NUMBER
```

3. After completion, report:
   - Findings count by severity
   - Patches generated and whether they passed tests
   - Total iterations used
   - Estimated cost from Weave trace
   - Link to W&B Weave run if available

If $REPO and $PR_NUMBER are not provided as arguments, ask the user for them before running.
