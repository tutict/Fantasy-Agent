from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fantasy_agent.contracts import DirectorBuildPlan, DirectorTaskBreakdown, PromptRequest
from fantasy_agent.local_tools import manual_correction_targets, open_manual_correction_target
from fantasy_agent.workflows import decompose_production_tasks, run_director_workflow

APP_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = APP_DIR / "static"

app = FastAPI(
    title="Fantasy Agent Flow Console",
    version="0.1.0",
    description="Local UI for prompt-to-playable multi-agent production planning.",
)

app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")


class ManualCorrectionOpenRequest(BaseModel):
    target_id: str
    engine: str = "UE5"
    confirmed_side_effects: bool = False


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "web-console"}


@app.post("/api/plan", response_model=DirectorBuildPlan)
def plan(request: PromptRequest) -> DirectorBuildPlan:
    return run_director_workflow(request)


@app.post("/api/tasks", response_model=DirectorTaskBreakdown)
def tasks(request: PromptRequest) -> DirectorTaskBreakdown:
    return decompose_production_tasks(request)


@app.get("/api/manual-correction/targets")
def correction_targets(engine: str = "UE5") -> dict[str, Any]:
    return manual_correction_targets(engine)


@app.post("/api/manual-correction/open")
def correction_open(request: ManualCorrectionOpenRequest) -> dict[str, Any]:
    return open_manual_correction_target(
        target_id=request.target_id,
        engine=request.engine,
        confirmed_side_effects=request.confirmed_side_effects,
    )
