import { useEffect, useMemo, useRef, useState } from "react";
import {
  adoptEvolution, cancelEvolution, getEvolution, getEvolutionExperiences,
  previewEvolution, startEvolution, suggestEvolution
} from "../../shared/api";
import type { Translator } from "../../shared/i18n";
import { usesGodotEngine } from "../../shared/planModel";
import { projectStore } from "../../shared/projectStore";
import type { ProjectBinding, ProjectSnapshot } from "../../shared/projectTypes";
import type {
  DirectorBuildPlan, EvolutionOptions, EvolutionReport, EvolutionSuggestion, NumericChange,
  ProductionSpecBundle
} from "../../shared/types";
import { Button, ConfirmDialog, StatusBadge } from "../../shared/ui/primitives";

const EXPERIMENT_KEY = "fantasy-agent.evolution.active-experiment";
const STATUS_KEYS: Record<string, string> = {
  running: "evolutionStatusRunning", improved: "evolutionStatusImproved",
  unchanged: "evolutionStatusUnchanged", manual_rework: "evolutionStatusManualRework",
  budget_exhausted: "evolutionStatusBudget", cancelled: "evolutionStatusCancelled",
  failed: "evolutionStatusFailed", interrupted: "evolutionStatusInterrupted"
};
const BADGE_STATUS: Record<string, string> = {
  running: "running", improved: "passed", unchanged: "warning", manual_rework: "blocked",
  budget_exhausted: "warning", cancelled: "cancelled", failed: "failed", interrupted: "blocked"
};
const FIELD_KEYS: Record<NumericChange["field"], string> = {
  "numeric.player_move_speed": "evolutionMoveSpeed",
  "numeric.pressure_clock_seconds": "evolutionClock",
  "numeric.enemy_pressure.enemy_count_multiplier": "evolutionEnemyCount",
  "numeric.enemy_pressure.move_speed_multiplier": "evolutionEnemySpeed",
  "numeric.enemy_pressure.detection_radius_multiplier": "evolutionDetection"
};

function savedExperiment(storageKey = EXPERIMENT_KEY): string | null {
  try {
    const value = localStorage.getItem(storageKey);
    return value && /^[a-zA-Z0-9_-]{1,96}$/.test(value) ? value : null;
  } catch {
    return null;
  }
}

function Changes({ changes, t }: { changes: NumericChange[]; t: Translator }) {
  return <ul>{changes.map((change) => (
    <li key={change.field}>
      <strong>{t(FIELD_KEYS[change.field])}</strong>: {change.before} → {change.after}
      <p className="ui-hint">{change.reason}</p>
    </li>
  ))}</ul>;
}

export function EvolutionPanel({ plan, binding, t, active = true, onAdoptBundle, onRunningChange, externalReport }: {
  plan: DirectorBuildPlan | null;
  binding?: ProjectBinding;
  externalReport?: EvolutionReport;
  t: Translator;
  active?: boolean;
  onAdoptBundle: (bundle: ProductionSpecBundle) => void;
  onRunningChange?: (running: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const [maxIterations, setMaxIterations] = useState(3);
  const [maxWallSeconds, setMaxWallSeconds] = useState(600);
  const [useExperience, setUseExperience] = useState(true);
  const [preview, setPreview] = useState<{ request: EvolutionOptions; key: string; effects: string[] } | null>(null);
  const storageKey = binding ? `${EXPERIMENT_KEY}:${binding.project_id}:${binding.plan_version}` : EXPERIMENT_KEY;
  const [experimentId, setExperimentId] = useState<string | null>(() => savedExperiment(storageKey));
  const [localReport, setReport] = useState<EvolutionReport | null>(null);
  const report = externalReport ?? localReport;
  const [polling, setPolling] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [suggestion, setSuggestion] = useState<{ value: EvolutionSuggestion; key: string } | null>(null);
  const [experienceCount, setExperienceCount] = useState<number | null>(null);
  const planKey = useMemo(() => JSON.stringify([binding?.project_id, binding?.plan_version, plan]), [binding?.project_id, binding?.plan_version, plan]);
  const currentPlanKey = useRef(planKey);
  currentPlanKey.current = planKey;
  const reviewKey = JSON.stringify([planKey, maxIterations, maxWallSeconds, useExperience]);
  const currentReviewKey = useRef(reviewKey);
  currentReviewKey.current = reviewKey;
  const canRun = Boolean(plan?.production_spec_bundle && usesGodotEngine(plan));
  const validBudget = Number.isInteger(maxIterations) && maxIterations >= 1 && maxIterations <= 3
    && Number.isFinite(maxWallSeconds) && maxWallSeconds >= 30 && maxWallSeconds <= 1800;

  useEffect(() => { setPreview(null); }, [reviewKey]);
  useEffect(() => { setSuggestion(null); }, [planKey]);
  useEffect(() => {
    setExperimentId(savedExperiment(storageKey)); setReport(null); setPolling(false);
    setError(""); setBusy(false); setExperienceCount(null);
  }, [storageKey]);
  useEffect(() => { onRunningChange?.(polling); }, [polling, onRunningChange]);

  useEffect(() => {
    if (!experimentId || (!active && !polling)) return;
    let abandoned = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const payload = await getEvolution(experimentId!);
        if (abandoned) return;
        setReport(payload.report);
        const running = payload.status === "running" || payload.status === "cancelling";
        setPolling(running);
        if (payload.error) setError(payload.error);
        if (payload.status === "unknown") setError(t("evolutionUnknown"));
        if (running) timer = setTimeout(() => void poll(), 1000);
      } catch (failure) {
        if (!abandoned) {
          setError(String(failure instanceof Error ? failure.message : failure));
          // A failed read cannot assert that the last known running worker ended.
          if (polling) timer = setTimeout(() => void poll(), 1000);
        }
      }
    }
    void poll();
    return () => { abandoned = true; if (timer) clearTimeout(timer); };
  }, [experimentId, active, polling, planKey, t]);

  async function reviewExperiment() {
    if (!plan || !canRun || !validBudget) return;
    const key = reviewKey;
    const request: EvolutionOptions = JSON.parse(JSON.stringify({
      ...binding, plan, max_iterations: maxIterations, max_wall_seconds: maxWallSeconds, use_experience: useExperience
    }));
    setBusy(true);
    setError("");
    try {
      const result = await previewEvolution(request);
      if (key !== currentReviewKey.current) return;
      setPreview({ request, key, effects: result.planned_side_effects });
    } catch (failure) {
      if (key === currentReviewKey.current) setError(String(failure instanceof Error ? failure.message : failure));
    } finally { if (key === currentReviewKey.current) setBusy(false); }
  }

  async function confirmExperiment(confirmedByUser: boolean) {
    if (!confirmedByUser) return;
    if (!preview || preview.key !== currentReviewKey.current) {
      setPreview(null); setError(t("evolutionPlanChanged")); return;
    }
    // This handler is called only by the user's confirmation button.
    const request = preview.request;
    const key = preview.key;
    setPreview(null);
    setBusy(true);
    setError("");
    try {
      const result = await startEvolution(request, confirmedByUser);
      if (key !== currentReviewKey.current) return;
      setExperimentId(result.experiment_id);
      setReport(null);
      setPolling(true);
      setOpen(true);
      try { localStorage.setItem(storageKey, result.experiment_id); }
      catch { setError(t("evolutionStorageError")); }
    } catch (failure) {
      if (key === currentReviewKey.current) setError(String(failure instanceof Error ? failure.message : failure));
    } finally { if (key === currentReviewKey.current) setBusy(false); }
  }

  async function cancelExperiment() {
    if (!experimentId) return;
    const key = planKey;
    setBusy(true);
    try {
      await cancelEvolution(experimentId);
    } catch (failure) {
      if (key === currentPlanKey.current) setError(String(failure instanceof Error ? failure.message : failure));
    } finally { if (key === currentPlanKey.current) setBusy(false); }
  }

  async function adoptCandidate() {
    if (!experimentId || !plan || polling) return;
    const key = planKey;
    setBusy(true); setError("");
    try {
      const result = await adoptEvolution(experimentId, plan, feedback, binding);
      if (key !== currentPlanKey.current) return;
      if (!result.plan.production_spec_bundle) throw new Error(t("evolutionNeedsPlan"));
      if (binding) {
        if (result.project_id !== binding.project_id || !Number.isInteger(result.plan_version)) throw new Error(t("evolutionPlanChanged"));
        projectStore.acceptSaved(result as ProjectSnapshot, binding);
      } else onAdoptBundle(result.plan.production_spec_bundle);
      setReport((current) => current ? { ...current, adopted_iteration: current.best_iteration } : current);
    } catch (failure) {
      if (key === currentPlanKey.current) setError(String(failure instanceof Error ? failure.message : failure));
    } finally { if (key === currentPlanKey.current) setBusy(false); }
  }

  async function readExperience() {
    if (!plan || !canRun) return;
    const key = planKey;
    setBusy(true); setError(""); setSuggestion(null);
    try {
      const [history, value] = await Promise.all([getEvolutionExperiences(), suggestEvolution(plan)]);
      if (currentPlanKey.current !== key || currentReviewKey.current !== reviewKey) return;
      setExperienceCount(history.experiences.length);
      setSuggestion({ value, key });
    } catch (failure) {
      if (key === currentPlanKey.current) setError(String(failure instanceof Error ? failure.message : failure));
    } finally { if (key === currentPlanKey.current) setBusy(false); }
  }

  const winner = report?.iterations.find((iteration) => iteration.index === report.best_iteration);
  return (
    <details className="evolution-fold" open={open || polling} data-panel="evolution">
      <summary onClick={(event) => { event.preventDefault(); setOpen((value) => !value); }}>
        <h2>{t("evolutionTitle")}</h2>
        {polling || report ? <StatusBadge status={polling ? "running" : BADGE_STATUS[report!.status]}
          label={t(STATUS_KEYS[polling ? "running" : report!.status])} /> : null}
        <svg className="evolution-chevron" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
          <path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </summary>
      <div className="rail-card-body">
        <p className="ui-hint">{t("evolutionHint")}</p>
        {!canRun ? <p className="ui-hint">{t("evolutionNeedsPlan")}</p> : null}
        <div className="evolution-controls">
        <label className="playtest-field"><span>{t("evolutionIterations")}</span>
          <input type="number" min={1} max={3} value={maxIterations} disabled={busy || polling}
            onChange={(event) => setMaxIterations(Number(event.target.value))} />
        </label>
        <label className="playtest-field"><span>{t("evolutionBudget")}</span>
          <input type="number" min={30} max={1800} value={maxWallSeconds} disabled={busy || polling}
            onChange={(event) => setMaxWallSeconds(Number(event.target.value))} />
        </label>
        </div>
        <label className="field-label"><input type="checkbox" checked={useExperience} disabled={busy || polling}
          onChange={(event) => setUseExperience(event.target.checked)} />{t("evolutionUseExperience")}</label>
        <div className="handoff-actions">
          <Button type="button" tone="primary" disabled={!canRun || !validBudget || busy || polling}
            onClick={() => void reviewExperiment()}>{t("evolutionPreview")}</Button>
          <Button type="button" disabled={!canRun || busy || polling} onClick={() => void readExperience()}>
            {t("evolutionReadExperience")}
          </Button>
          {experimentId && (polling || (!report && error)) ? <Button type="button" disabled={busy}
            onClick={() => void cancelExperiment()}>{t("stopJob")}</Button> : null}
        </div>
        {busy ? <p className="ui-hint" role="status">{t("operationRunning")}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
        {experienceCount !== null ? <p className="ui-hint">{t("evolutionExperienceCount", { count: experienceCount })}</p> : null}
        {suggestion ? <div>
          <Changes changes={suggestion.value.changes} t={t} />
          {suggestion.value.notes.map((note, index) => <p className="ui-hint" key={index}>{note}</p>)}
          {suggestion.value.changes.length ? <Button type="button" disabled={busy || polling}
            onClick={() => {
              if (suggestion.key === planKey && suggestion.value.plan.production_spec_bundle)
                onAdoptBundle(suggestion.value.plan.production_spec_bundle);
            }}>{t("evolutionApplyExperience")}</Button> : null}
        </div> : null}
        {report ? <div>
          <p className="evolution-summary">
            {t("evolutionCompletedCandidates", { count: report.iterations.filter((item) => item.index > 0).length })}
            {" · "}{t("evolutionElapsed", { seconds: Math.round(report.elapsed_seconds) })}
          </p>
          {report.notes.map((note, index) => <p className="ui-hint" key={index}>{note}</p>)}
          {(report.risks ?? []).map((risk, index) => <p className="ui-hint" key={`risk-${index}`}>{risk}</p>)}
          {report.iterations.map((iteration) => <details key={iteration.index}
            open={iteration.index === report.best_iteration || (report.status === "manual_rework" && iteration.index === 0)}>
            <summary>{iteration.index === 0 ? t("evolutionBaseline") : t("evolutionCandidate", { index: iteration.index })}</summary>
            {iteration.report?.aggregate ? <p>
              {t("playtestOutcomes")}: {iteration.report.aggregate.wins ?? 0} / {iteration.report.aggregate.failures ?? 0} / {iteration.report.aggregate.timeouts ?? 0}
              {" · "}{t("playtestSessionSeconds")}: {iteration.report.aggregate.session_seconds_p50 ?? 0}s
            </p> : <p>{t("evolutionUnmeasured")}</p>}
            {iteration.report?.project_dir ? <p className="ui-hint">
              {t("playtestProject")}: <code>{iteration.report.project_dir}</code>
            </p> : null}
            <ul>{iteration.report?.findings?.map((finding, index) => (
              <li key={`${finding.code}-${index}`}>
                <strong>{finding.code}</strong><p>{finding.message}</p>
                {finding.rework_target ? <p className="ui-hint">{t("playtestReworkTarget")}: {finding.rework_target}</p> : null}
              </li>
            ))}</ul>
            <Changes changes={iteration.changes} t={t} />
            {iteration.notes.map((note, index) => <p className="ui-hint" key={index}>{note}</p>)}
          </details>)}
          {(report.next_actions ?? []).map((action, index) => <p className="ui-hint" key={`action-${index}`}>{action}</p>)}
          {report.adopted_iteration !== null ? <p role="status">{t("evolutionAdopted")}</p> : !externalReport && winner?.eligible && report.status === "improved" ? <div>
            <label className="field-label" htmlFor="evolution-feedback">{t("evolutionFeedback")}</label>
            <textarea id="evolution-feedback" rows={2} maxLength={4000} value={feedback} onChange={(event) => setFeedback(event.target.value)} />
            <Button type="button" disabled={busy || polling || !plan} onClick={() => void adoptCandidate()}>{t("evolutionAdopt")}</Button>
          </div> : null}
        </div> : null}
      </div>
      <ConfirmDialog open={Boolean(preview)} title={t("evolutionConfirmTitle")}
        body={t("evolutionConfirmHint")}
        confirmLabel={t("evolutionConfirmStart")} cancelLabel={t("generateConfirmCancel")}
        onConfirm={(confirmedByUser) => void confirmExperiment(confirmedByUser)} onCancel={() => setPreview(null)}>
        <ul className="evolution-effects">{(preview?.effects ?? []).map((effect, index) => <li key={index}>{effect}</li>)}</ul>
      </ConfirmDialog>
    </details>
  );
}
