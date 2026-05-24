from fastapi import FastAPI

from fantasy_agent.contracts import GameplaySpec, UnrealProjectPlan
from fantasy_agent.workflows import prepare_unreal_project

app = FastAPI(
    title="Fantasy Agent Unreal Builder",
    version="0.1.0",
    description="Prepares UE5-compatible project automation plans.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "unreal-builder"}


@app.post("/prepare", response_model=UnrealProjectPlan)
def prepare(spec: GameplaySpec) -> UnrealProjectPlan:
    return prepare_unreal_project(spec)
