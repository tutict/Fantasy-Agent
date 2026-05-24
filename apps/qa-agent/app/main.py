from fastapi import FastAPI

from fantasy_agent.contracts import GameplaySpec, QAPlan
from fantasy_agent.workflows import prepare_qa_plan

app = FastAPI(
    title="Fantasy Agent QA Agent",
    version="0.1.0",
    description="Generates prototype QA and packaging checks from gameplay specs.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "qa-agent"}


@app.post("/qa", response_model=QAPlan)
def qa(spec: GameplaySpec) -> QAPlan:
    return prepare_qa_plan(spec)
