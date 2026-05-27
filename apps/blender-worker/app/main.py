from fastapi import FastAPI

from fantasy_agent.blender_codegen import build_blender_script_artifact
from fantasy_agent.contracts import BlenderAssetPlan, BlenderScriptArtifact, GameplaySpec
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


@app.post("/script", response_model=BlenderScriptArtifact)
def script(plan: BlenderAssetPlan) -> BlenderScriptArtifact:
    return build_blender_script_artifact(plan)


@app.post("/assets/script", response_model=BlenderScriptArtifact)
def assets_script(spec: GameplaySpec) -> BlenderScriptArtifact:
    return build_blender_script_artifact(prepare_blender_assets(spec))
