from fastapi import FastAPI

from fantasy_agent.contracts import ComfyUIVisualPlan, GameplaySpec
from fantasy_agent.workflows import prepare_comfyui_visuals

app = FastAPI(
    title="Fantasy Agent ComfyUI Worker",
    version="0.1.0",
    description="Prepares gameplay-readable ComfyUI visual reference jobs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "comfyui-worker"}


@app.post("/visuals", response_model=ComfyUIVisualPlan)
def visuals(spec: GameplaySpec) -> ComfyUIVisualPlan:
    return prepare_comfyui_visuals(spec)
