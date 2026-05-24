from fastapi import FastAPI

from fantasy_agent.contracts import BlenderAssetPlan, GameplaySpec
from fantasy_agent.workflows import prepare_blender_assets

app = FastAPI(
    title="Fantasy Agent Blender Worker",
    version="0.1.0",
    description="Prepares procedural Blender asset generation jobs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "blender-worker"}


@app.post("/assets", response_model=BlenderAssetPlan)
def assets(spec: GameplaySpec) -> BlenderAssetPlan:
    return prepare_blender_assets(spec)
