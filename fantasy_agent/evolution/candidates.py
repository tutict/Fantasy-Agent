"""Small numeric proposals; generated code and win rules are never edited."""

import hashlib
import json
import math

from fantasy_agent.contracts import DirectorBuildPlan, PlaytestReport
from fantasy_agent.evolution.contracts import EvolutionExperience, NumericChange
from fantasy_agent.gameplay_codegen import axis_for_spec
from fantasy_agent.spec_validation import validate_production_spec_bundle


def plan_fingerprint(plan: DirectorBuildPlan) -> str:
    raw = json.dumps(plan.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_changes(plan: DirectorBuildPlan, changes: list[NumericChange]) -> DirectorBuildPlan:
    if plan.production_spec_bundle is None:
        raise ValueError("数值进化需要 ProductionSpecBundle。")
    payload = plan.model_dump(mode="python")
    seen: set[str] = set()
    for raw in changes:
        change = NumericChange.model_validate(raw)
        if change.field in seen:
            raise ValueError("同一个参数不能在一份候选中重复修改。")
        seen.add(change.field)
        fields = change.field.split(".")
        owner = payload["production_spec_bundle"]
        for field in fields[:-1]:
            owner = owner[field]
        if not math.isclose(float(owner[fields[-1]]), change.before, rel_tol=1e-9):
            raise ValueError(f"{change.field} 的原值已变化，请重新生成建议。")
        if change.field == "numeric.pressure_clock_seconds" and not change.after.is_integer():
            raise ValueError("压力时钟必须是整数秒。")
        owner[fields[-1]] = int(change.after) if change.field.endswith("clock_seconds") else change.after
    updated = DirectorBuildPlan.model_validate(payload)
    validation = validate_production_spec_bundle(updated.production_spec_bundle)
    if validation.status == "failed":
        raise ValueError("候选超出当前 Spec 的数值范围：" + "; ".join(i.message for i in validation.issues))
    updated.production_spec_bundle.validation = validation
    return updated


def _change(plan: DirectorBuildPlan, field: str, factor: float, reason: str) -> list[NumericChange]:
    bundle = plan.production_spec_bundle
    if bundle is None:
        return []
    owner = bundle.model_dump(mode="python")
    for part in field.split("."):
        owner = owner[part]
    before = float(owner)
    after = before * factor
    bounds = bundle.numeric.tuning_bounds.get(field.split(".")[-1])
    if bounds:
        after = min(bounds[1], max(bounds[0], after))
    if field.endswith("clock_seconds"):
        after = float(min(1800, round(after)))
    if math.isclose(before, after):
        return []
    change = NumericChange(field=field, before=before, after=after, reason=reason)
    try:
        apply_changes(plan, [change])
    except ValueError:
        return []
    return [change]


def propose_changes(plan: DirectorBuildPlan, report: PlaytestReport) -> list[NumericChange]:
    if not report.samples or any(sample.script_errors or sample.missing_actions for sample in report.samples):
        return []
    reasons = " ".join(sample.reason for sample in report.samples if sample.outcome == "fail").casefold()
    if any(word in reasons for word in ("timer", "clock", "pressure", "计时", "时钟", "压力")):
        return _change(plan, "numeric.pressure_clock_seconds", 1.2, "计时失败，增加有限的路线时间余量。")
    if any(word in reasons for word in ("enemy", "enemies", "caught", "敌人", "侦测", "追捕")):
        return _change(plan, "numeric.enemy_pressure.move_speed_multiplier", 0.85,
                       "敌人压力导致失败，小幅降低追击速度后复测。")
    return []


def changes_from_experience(plan: DirectorBuildPlan, experience: EvolutionExperience) -> list[NumericChange]:
    if axis_for_spec(plan.gameplay_spec) != experience.axis:
        return []
    changes: list[NumericChange] = []
    for change in experience.changes:
        if change.before <= 0:
            return []
        proposal = _change(plan, change.field, change.after / change.before,
                           f"采用已复测经验 {experience.id}：{change.reason}")
        if not proposal:
            return []
        changes.extend(proposal)
    try:
        apply_changes(plan, changes)
    except ValueError:
        return []
    return changes
