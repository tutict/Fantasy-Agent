from fastapi import FastAPI

from fantasy_agent.contracts import GameplaySpec, PromptRequest
from fantasy_agent.generation import design_from_prompt

app = FastAPI(
    title="Fantasy Agent Gameplay Agent",
    version="0.1.0",
    description="Generates gameplay-first structured prototype specs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "gameplay-agent"}


@app.post("/design", response_model=GameplaySpec)
def design(request: PromptRequest) -> GameplaySpec:
    return design_from_prompt(request)
