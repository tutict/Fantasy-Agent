from fastapi import FastAPI

from fantasy_agent.contracts import DirectorBuildPlan, PromptRequest
from fantasy_agent.mcp import initial_mcp_contracts
from fantasy_agent.workflows import run_director_workflow

app = FastAPI(
    title="Fantasy Agent Director",
    version="0.1.0",
    description="Orchestrates prompt-to-playable prototype planning.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "director-agent"}


@app.get("/mcp/contracts")
def mcp_contracts():
    return initial_mcp_contracts()


@app.post("/plan", response_model=DirectorBuildPlan)
def plan(request: PromptRequest) -> DirectorBuildPlan:
    return run_director_workflow(request)
