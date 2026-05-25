import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import weave
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.graph import review_graph
from core.state import initial_state

_executor = ThreadPoolExecutor(max_workers=4)
_runs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.wandb_api_key:
        weave.init("autoreview-agent")
    yield
    _executor.shutdown(wait=False)


app = FastAPI(title="AutoReview Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    repo: str
    pr_number: int


class ReviewResponse(BaseModel):
    run_id: str
    status: str


def _run_review(run_id: str, repo: str, pr_number: int) -> None:
    try:
        _runs[run_id]["status"] = "running"
        state = initial_state(repo_slug=repo, pr_number=pr_number)
        result = review_graph.invoke(state)
        _runs[run_id].update(
            {
                "status": "complete",
                "findings": result.get("findings", []),
                "patches": len(result.get("patches", [])),
                "test_passed": result.get("test_passed", False),
                "iterations": result.get("iteration", 0),
                "input_tokens": result.get("input_tokens", 0),
                "output_tokens": result.get("output_tokens", 0),
            }
        )
    except Exception as exc:
        _runs[run_id].update({"status": "error", "error": str(exc)})


@app.post("/review", response_model=ReviewResponse, status_code=202)
async def start_review(req: ReviewRequest) -> ReviewResponse:
    run_id = str(uuid.uuid4())
    _runs[run_id] = {"status": "queued", "repo": req.repo, "pr_number": req.pr_number}
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_executor, _run_review, run_id, req.repo, req.pr_number)
    return ReviewResponse(run_id=run_id, status="queued")


@app.get("/status/{run_id}")
async def get_status(run_id: str) -> dict:
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return _runs[run_id]


@app.get("/runs")
async def list_runs() -> dict:
    return {"runs": [{"run_id": k, **v} for k, v in _runs.items()]}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
