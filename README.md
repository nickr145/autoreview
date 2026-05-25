# AutoReview Agent

An autonomous AI code review system. Paste a GitHub repo and PR number into the web UI — three Claude agents collaborate to detect vulnerabilities, generate patches, validate them in a sandboxed environment, and post inline comments directly on the PR.

---

## How it works

```
POST /review
    └── fetcher_node      fetches unified diff via GitHub API
    └── auditor_node      Bandit static analysis + Claude (extended thinking)
    └── quality_node      ruff/radon + Claude patch generation
    └── test_runner_node  applies patches → Docker sandbox (syntax + Bandit + ruff)
         └── if tests fail and iterations < 3: loop back to quality_node
    └── publisher_node    posts inline PR comments + cost summary via PyGithub
```

The self-correction loop gives the quality agent up to 3 attempts to produce a patch that passes sandbox validation before publishing whatever it has.

---

## Tech stack

| Layer | Technology |
|---|---|
| Agentic framework | LangGraph ≥ 0.2 |
| LLM | Anthropic Claude API (`claude-sonnet-4-6`, `claude-haiku-4-5`) |
| GitHub integration | PyGithub ≥ 2.3 |
| Static analysis | Bandit (security), ruff (style), radon (complexity) |
| Sandbox | Docker + Docker SDK for Python |
| Observability | Weights & Biases Weave (`@weave.op()`) |
| Backend | FastAPI + uvicorn |
| Frontend | React + Vite |
| Package manager | uv |
| Config | Pydantic Settings + `.env` |
| CLI | Typer |

---

## Project structure

```
autoreview/
├── agents/
│   ├── auditor.py        # Bandit + Claude extended thinking
│   ├── quality.py        # ruff/radon + Claude patch generation
│   ├── test_runner.py    # Docker sandbox validation
│   └── publisher.py      # PyGithub inline comments
├── core/
│   ├── graph.py          # LangGraph StateGraph + self-correction edge
│   ├── state.py          # ReviewState TypedDict
│   ├── sandbox.py        # Docker SDK helpers (network_mode=none)
│   └── github_client.py  # diff fetch + review post
├── tools/
│   ├── bandit_tool.py    # Bandit subprocess wrapper
│   ├── patch_tool.py     # unified diff apply + dry-run validation
│   ├── diff_tool.py      # extract changed files from PR diff
│   └── llm_tool.py       # @weave.op() Claude tool-use loop
├── api/
│   └── main.py           # FastAPI: POST /review, GET /status/{id}, GET /runs
├── frontend/             # React + Vite web UI
├── tests/
│   ├── fixtures/         # 6 seeded CVE-pattern Python files
│   ├── test_agents.py    # unit tests (LLM + Docker mocked)
│   └── test_fixtures.py  # Bandit recall accuracy tests
├── Dockerfile.sandbox    # ephemeral execution environment
├── Dockerfile            # API service
├── docker-compose.yml
└── cli.py                # Typer CLI
```

---

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (running)
- Anthropic API key
- GitHub fine-grained PAT with `contents:read` + `pull-requests:write`
- Weights & Biases account (for Weave tracing)

### Install

```bash
git clone https://github.com/nickr145/autoreview
cd autoreview

uv sync --dev
cp .env.example .env
# fill in ANTHROPIC_API_KEY, GITHUB_TOKEN, WANDB_API_KEY
```

### Build the sandbox image

The test runner executes patches inside an ephemeral Docker container with no network access:

```bash
docker build -t autoreview-sandbox:latest -f Dockerfile.sandbox .
```

---

## Running

### Full stack (API + React UI)

```bash
docker compose up --build
```

- Web UI: http://localhost:5173
- API docs: http://localhost:8000/docs

### CLI (one-shot review)

```bash
uv run python cli.py run --repo owner/repo --pr 42
```

### API only (dev)

```bash
uv run uvicorn api.main:app --reload
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/review` | Start a review — returns `run_id` immediately (202). |
| `GET` | `/status/{run_id}` | Poll run status and results. |
| `GET` | `/runs` | List all runs (in-process). |
| `GET` | `/health` | Health check. |

**Start a review:**
```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"repo": "owner/repo", "pr_number": 42}'
# → {"run_id": "abc-123", "status": "queued"}
```

**Poll for results:**
```bash
curl http://localhost:8000/status/abc-123
# → {"status": "complete", "findings": [...], "patches": 2, "test_passed": true, "input_tokens": 12400, ...}
```

---

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required |
| `GITHUB_TOKEN` | — | Fine-grained PAT: contents:read + pull-requests:write |
| `WANDB_API_KEY` | — | Required for Weave tracing |
| `MAX_ITERATIONS` | `3` | Hard cap on self-correction loop |
| `THINKING_BUDGET_TOKENS` | `8000` | Extended thinking budget for the auditor |
| `THINKING_ENABLED` | `true` | Set `false` to skip extended thinking (faster, cheaper) |
| `SANDBOX_MEM_LIMIT` | `512m` | Docker container memory limit |
| `CLAUDE_AUDITOR_MODEL` | `claude-sonnet-4-6` | |
| `CLAUDE_QUALITY_MODEL` | `claude-sonnet-4-6` | |
| `CLAUDE_PUBLISHER_MODEL` | `claude-haiku-4-5` | |

---

## Tests

```bash
# Unit tests — all LLM + Docker calls mocked, runs in ~2s
uv run pytest tests/test_agents.py -v

# Bandit recall accuracy against the fixture suite
uv run pytest tests/test_fixtures.py -v

# Full suite
uv run pytest tests/ -v
```

The fixture suite contains 6 Python files with seeded CVE patterns (SQL injection, hardcoded secrets, path traversal, insecure deserialization, shell injection, weak crypto). The accuracy test enforces ≥ 80% Bandit recall — currently 100%.

---

## Design decisions

**No full repo clone.** The agent only sees the PR diff — it never clones the git history, which may contain deleted secrets. Bandit runs on the added lines extracted from the diff.

**`network_mode=none` on all sandbox containers.** Prevents prompt-injection payloads in reviewed code from exfiltrating environment variables or calling external endpoints.

**`MAX_ITERATIONS=3` is a hard cap.** An uncapped self-correction loop burns API budget on a single malformed file. The publisher posts whatever state the agent reached after 3 attempts.

**Extended thinking on the auditor only.** The auditor needs to reason carefully about whether a finding is a genuine vulnerability vs. a false positive. Quality and publisher agents run in standard mode to keep cost low.

**Token cost flows through state.** Each agent node returns `input_tokens` + `output_tokens`. LangGraph accumulates them across nodes via `operator.add` reducers, so the publisher can report exact usage and estimated cost in the PR summary comment.

---

## Portfolio targets

| Metric | Target |
|---|---|
| Cost per review | < $0.05 |
| Bandit recall on fixture suite | ≥ 80% |
| Patch success rate (≤ 3 iterations) | ≥ 75% |
| Review latency p95 | < 90s |
