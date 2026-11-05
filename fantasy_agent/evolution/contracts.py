"""Contracts for measured numeric experiments; approvals are request-only."""

from typing import Literal

from pydantic import Field

from fantasy_agent.contracts import DirectorBuildPlan, PlaytestReport, StrictModel

NumericField = Literal[
    "numeric.player_move_speed",
    "numeric.pressure_clock_seconds",
    "numeric.enemy_pressure.enemy_count_multiplier",
    "numeric.enemy_pressure.move_speed_multiplier",
    "numeric.enemy_pressure.detection_radius_multiplier",
]


class NumericChange(StrictModel):
    field: NumericField
    before: float = Field(allow_inf_nan=False)
    after: float = Field(allow_inf_nan=False)
    reason: str = Field(min_length=1)


class EvolutionRequest(StrictModel):
    plan: DirectorBuildPlan
    confirmed: bool = False
    max_iterations: int = Field(default=3, ge=1, le=3)
    max_wall_seconds: float = Field(default=600.0, ge=30.0, le=1800.0)
    use_experience: bool = True


class EvolutionIteration(StrictModel):
    index: int = Field(ge=0)
    session_id: str
    plan: DirectorBuildPlan
    report: PlaytestReport | None = None
    changes: list[NumericChange] = Field(default_factory=list)
    eligible: bool = False
    improved: bool = False
    notes: list[str] = Field(default_factory=list)


class EvolutionReport(StrictModel):
    source: str = "fantasy-agent.evolution"
    schema_version: Literal["0.1"] = "0.1"
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=lambda: ["脚本 bot 的结果不能代替人工试玩。"])
    next_actions: list[str] = Field(default_factory=list)
    experiment_id: str
    status: Literal[
        "running", "improved", "unchanged", "manual_rework", "budget_exhausted",
        "cancelled", "failed", "interrupted",
    ]
    original_plan: DirectorBuildPlan
    iterations: list[EvolutionIteration] = Field(default_factory=list)
    best_iteration: int | None = None
    adopted_iteration: int | None = None
    notes: list[str] = Field(default_factory=list)
    elapsed_seconds: float = Field(default=0.0, ge=0.0)


class EvolutionExperience(StrictModel):
    id: str
    experiment_id: str
    axis: str
    engine: Literal["Godot 4"] = "Godot 4"
    changes: list[NumericChange] = Field(default_factory=list)
    feedback: str = Field(default="", max_length=4000)
    created_at: str = ""


class ExperienceIndex(StrictModel):
    schema_version: Literal["0.1"] = "0.1"
    experiences: list[EvolutionExperience] = Field(default_factory=list)
