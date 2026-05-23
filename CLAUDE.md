# AutoReview Agent — Project Context

## What This Is
An autonomous AI code review system. A user pastes a GitHub repo + PR number into a web UI; three LLM agents collaborate to detect vulnerabilities, generate patches, validate them in a Docker sandbox, and post inline comments directly on the PR.

## Architecture

```
Web UI (React)
    ↓ POST /review
FastAPI backend
    ↓
LangGraph StateGraph
    ├── auditor_node    → Bandit + Claude (extended thinking)
    ├── quality_node    → ruff/ESLint + Claude (patch generation)
    ├── test_runner     → pytest/Jest inside Docker sandbox
    └── publisher_node  → PyGithub inline PR comments + summary
```

Self-correction loop: test_runner → quality_node (max 3 retries) → publisher_node.

## Directory Structure

```
autoreview/
├── agents/
│   ├── auditor.py          # Auditor Agent node + system prompt
│   ├── quality.py          # Quality Agent node + system prompt
│   ├── test_runner.py      # Test Runner node
│   └── publisher.py        # Publisher node (GitHub API)
├── core/
│   ├── graph.py            # LangGraph StateGraph wiring
│   ├── state.py            # ReviewState TypedDict
│   ├── sandbox.py          # Docker SDK helpers
│   └── github_client.py    # PyGithub wrapper
├── tools/
│   ├── bandit_tool.py      # Bandit subprocess + JSON parse
│   ├── patch_tool.py       # Apply/validate unified diffs
│   └── llm_tool.py         # @weave.op() wrapped Claude tool loop
├── api/
│   └── main.py             # FastAPI app — POST /review, GET /status/{run_id}
├── frontend/               # React app (Vite)
│   ├── src/
│   └── package.json
├── tests/
│   ├── fixtures/           # Seeded buggy Python/TS files (CVE patterns)
│   └── test_agents.py      # Unit tests — mock LLM + Docker SDK
├── .github/workflows/
│   └── autoreview.yml      # CI: build sandbox image, run tests
├── Dockerfile.sandbox      # Ephemeral execution environment
├── docker-compose.yml      # Orchestrates agent + frontend services
├── .autoreview.yml         # Per-repo config schema
├── cli.py                  # Typer CLI (autoreview run --repo --pr)
├── pyproject.toml
└── .env
```

## Tech Stack

| Layer | Technology |
|---|---|
| Agentic framework | LangGraph ≥ 0.2 |
| LLM | Anthropic Claude API (anthropic Python SDK) |
| GitHub integration | PyGithub ≥ 2.3 |
| Static analysis | Bandit (Python), ruff, ESLint security plugin (TS) |
| Sandbox | Docker + Docker SDK for Python |
| Test execution | pytest (Python) / Jest (TS) inside Docker |
| Observability | Weights & Biases Weave (@weave.op()) |
| Backend | FastAPI |
| Frontend | React + Vite |
| Package manager | uv |
| Config | Pydantic Settings + .env |
| CLI | Typer |

## Model Assignments

| Agent | Model | Mode |
|---|---|---|
| Auditor | claude-sonnet-4-6 | Extended thinking (budget_tokens=8000) |
| Quality | claude-sonnet-4-6 | Standard |
| Test Runner | claude-sonnet-4-6 | Standard |
| Publisher | claude-haiku-4-5 | Standard |

## Critical Constraints

- **MAX_ITERATIONS = 3** — hard cap on self-correction loop. Never remove this; an uncapped loop burns API budget on a single malformed file.
- **network_mode='none'** on all Docker containers — prevents prompt-injection payloads from exfiltrating env vars or calling external endpoints.
- Repo is mounted **read-only** for analysis. Only a scratch copy is written to during patch application.
- **No full repo clone** — review the PR diff only. Never clone full history (may contain deleted secrets).
- Extended thinking is **Auditor only** — do not enable it on Quality or Publisher.

## Environment Variables

```
ANTHROPIC_API_KEY       # Required
GITHUB_TOKEN            # Fine-grained PAT: contents:write + pull-requests:write
WANDB_API_KEY           # Required for Weave tracing
MAX_ITERATIONS=3
CLAUDE_AUDITOR_MODEL=claude-sonnet-4-6
CLAUDE_QUALITY_MODEL=claude-sonnet-4-6
CLAUDE_PUBLISHER_MODEL=claude-haiku-4-5
THINKING_BUDGET_TOKENS=8000
THINKING_ENABLED=true
SANDBOX_MEM_LIMIT=512m
LOG_LEVEL=INFO
```

## Development Commands

```bash
# Install dependencies
uv sync

# Build Docker sandbox image
docker build -t autoreview-sandbox:latest -f Dockerfile.sandbox .

# Start full stack (FastAPI + React dev)
docker compose up

# Run agent unit tests
uv run pytest tests/ -v

# Lint
uv run ruff check .

# CLI one-shot review
uv run python cli.py run --repo owner/repo --pr 42
```

## Portfolio Metrics (targets)

| Metric | Target |
|---|---|
| Cost per review | < $0.05 |
| Vulnerability recall on fixture suite | ≥ 80% |
| Patch success rate (≤ 3 iterations) | ≥ 75% |
| Review latency p95 | < 90s |

## Sprint Roadmap

- **S1**: Dockerfile.sandbox + Docker SDK helper + LangGraph skeleton (stubs, no LLM)
- **S2**: Auditor Agent (Bandit + Claude) + Quality Agent (patch generation)
- **S3**: Test Runner + self-correction conditional edge
- **S4**: Publisher (PyGithub) + W&B Weave instrumentation + FastAPI backend
- **S5**: React frontend + fixture suite + accuracy measurement + polish
