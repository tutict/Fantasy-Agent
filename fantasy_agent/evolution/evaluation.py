"""Fixed acceptance checks, independent of the candidate proposer."""

from fantasy_agent.contracts import PlaytestReport
from fantasy_agent.godot_playtest import MIN_PLAYER_MOVE_METERS, aggregate_samples, build_findings
from fantasy_agent.playtest_bot import BOT_POLICIES


def measurement_notes(report: PlaytestReport) -> list[str]:
    """Evidence completeness; a reported aggregate is never the evidence."""
    notes: list[str] = []
    samples = report.samples
    if report.runs_requested < 1 or len(samples) != report.runs_requested:
        notes.append("试玩样本不完整，不能作为改进证据。")
    if {sample.run_index for sample in samples} != set(range(report.runs_requested)):
        notes.append("试玩样本编号重复或缺失。")
    axes = {sample.axis for sample in samples}
    if len(axes) != 1 or not axes <= set(BOT_POLICIES):
        notes.append("未测得明确且受支持的机制轴。")
    if any(sample.outcome not in {"win", "fail", "timeout"} for sample in samples):
        notes.append("试玩结果不可读。")
    return notes


def candidate_notes(report: PlaytestReport) -> list[str]:
    notes = measurement_notes(report)
    aggregate = aggregate_samples(report.samples)
    findings = [*report.findings, *build_findings(report.samples, aggregate)]
    if any(finding.severity == "blocking" for finding in findings):
        notes.append("候选仍有阻断性试玩问题。")
    if not aggregate.wins:
        notes.append("候选没有测得可达的胜利路径。")
    for sample in report.samples:
        if not sample.playable or sample.degraded:
            notes.append("候选包含不可玩或降级样本。")
        if sample.script_errors or sample.missing_actions:
            notes.append("候选存在脚本错误或缺失输入动作。")
        if sample.session_seconds <= 0 or sample.player_moved_distance < MIN_PLAYER_MOVE_METERS:
            notes.append("候选没有测得实际移动和局内时长。")
        policy = BOT_POLICIES.get(sample.axis)
        delivered = set(sample.held) | {key for key, count in sample.taps.items() if count > 0}
        if policy is None or not policy.actions <= delivered:
            notes.append("候选未交付该机制轴的核心动作。")
        if policy is not None:
            for metric in policy.priced:
                if getattr(sample, metric) <= 0:
                    notes.append(f"候选未测得核心动作对 {metric} 的作用。")
    return list(dict.fromkeys(notes))


def compare_reports(baseline: PlaytestReport, candidate: PlaytestReport) -> tuple[bool, list[str]]:
    notes = [*measurement_notes(baseline), *candidate_notes(candidate)]
    if baseline.runs_requested != candidate.runs_requested:
        notes.append("基线与候选的试玩次数不一致。")
    if {sample.axis for sample in baseline.samples} != {sample.axis for sample in candidate.samples}:
        notes.append("基线与候选的机制轴不一致。")
    # Compare presence of measured effects, not raw tap counts: reaching the
    # same exit sooner legitimately needs fewer presses and frames.
    for metric in ("enemy_hp_lost", "stamina_spent"):
        if any(getattr(sample, metric) > 0 for sample in baseline.samples) and not all(
            getattr(sample, metric) > 0 for sample in candidate.samples
        ):
            notes.append(f"已有的 {metric} 机制作用发生退化。")
    if notes:
        return False, list(dict.fromkeys(notes))
    before = aggregate_samples(baseline.samples)
    after = aggregate_samples(candidate.samples)
    old_blocks = {finding.code for finding in build_findings(baseline.samples, before)
                  if finding.severity == "blocking"}
    new_blocks = {finding.code for finding in build_findings(candidate.samples, after)
                  if finding.severity == "blocking"}
    improved = after.wins > before.wins or (after.wins >= before.wins and len(new_blocks) < len(old_blocks))
    return improved, [
        f"胜利次数 {before.wins}/{before.runs} → {after.wins}/{after.runs}。",
        "通过固定检查；仍需人工试玩判断体验。" if improved else "没有测得改善，保留原计划。",
    ]
