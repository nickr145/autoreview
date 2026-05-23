# Run Tests

Run the agent unit test suite. All LLM calls and Docker SDK calls are mocked — tests should be fast and deterministic.

## Steps

1. Run the full test suite with verbose output:
```bash
.venv/bin/python -m pytest tests/ -v --tb=short
```

2. If any tests fail, show the full failure output and identify:
   - Which agent node failed
   - Whether it's an LLM mock issue, a state schema issue, or a routing issue
   - A suggested fix

3. Run with coverage if requested:
```bash
.venv/bin/python -m pytest tests/ -v --cov=agents --cov=core --cov=tools --cov-report=term-missing
```

Report: total passed/failed, any failures with root cause, coverage summary if run.
