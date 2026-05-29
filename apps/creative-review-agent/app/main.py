from fastapi import FastAPI

from fantasy_agent.contracts import CreativeReviewReport, CreativeReviewRequest
from fantasy_agent.workflows import prepare_creative_review

app = FastAPI(
    title="Fantasy Agent Creative Review Agent",
    version="0.1.0",
    description=(
        "Prepares user-facing review gates for ComfyUI references and Blender assets before "
        "Unreal ingest."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "creative-review-agent"}


@app.post("/review", response_model=CreativeReviewReport)
def review(request: CreativeReviewRequest) -> CreativeReviewReport:
    return prepare_creative_review(
        request.gameplay_spec,
        request.blender_plan,
        request.comfyui_plan,
    )
