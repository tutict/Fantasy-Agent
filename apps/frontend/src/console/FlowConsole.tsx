import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { projectStore, useProject } from "../shared/projectStore";
import { WorkflowJobs, currentWorkflowResult } from "../shared/WorkflowJobs";
import { useJourney } from "../shared/journeyContext";
import { operationPhase, operationReason, JOURNEY_STEP_KEYS, type JourneyStepId } from "../shared/productionJourney";
import { ConfirmDialog, LogBlock, StatusBadge } from "../shared/ui/primitives";
import type { ReactNode } from "react";
import {
  inspectCorrections,
  openManualCorrectionTarget as openManualCorrectionTargetApi,
  previewAssetExecution,
  previewExecute,
  previewPlaytest,
  startAssetExecution,
  startExecute,
  startPlaytest,
  getSessionState,
  getOrchestrationState
} from "../shared/api";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import { useLocaleTheme } from "../shared/localeTheme";
import type {
  CorrectionMode,
  CorrectionReport,
  EnemyPressureTuning,
  ExecuteResult,
  ExecuteStage,
  Locale,
  ManualCorrectionTarget,
  PlaytestReport,
  PlaytestResult,
  SessionState,
  StatusState,
  OrchestrationSession,
  Theme
} from "../shared/types";
import { readOrchestrationEngine, readOrchestrationSessionId } from "../shared/storage";
import {
  GateItem,
  ReviewPanel,
  SpecBundlePanel,
  SpecRegenPanel,
  selectedEngineVersion,
  statusLabel,
  usesGodotEngine
} from "./rendering";
import {
  useActivityLog,
  useApprovalManifest,
  useAssetJobPolling,
  useCorrections,
  useDemoJobPolling,
  useEnemyTuning,
  useManualTargets,
  usePlaytestJobPolling,
  usePlanningHandoff,
  useSessionState,
  useSpecPreview,
  useSpecRegen
} from "./hooks";
import "../styles/console.css";
import { EvolutionPanel } from "./evolution/EvolutionPanel";

const correctionModeKeys: Record<CorrectionMode, string> = {
  gameplay: "modeGameplay",
  visuals: "modeVisuals",
  scope: "modeScope",
  import: "modeImport"
};

/**
 * The four panels of the plan rail. These double as the `data-panel` values the
 * tests select on, so a card's identity lives in one string and not in a class
 * name that a later restyle would move.
 */
type PlanCardKey = "handoff" | "correction" | "manual-correction" | "operator";

const correctionModeManualTargets: Record<CorrectionMode, string> = {
  gameplay: "planning",
  visuals: "comfyui",
  scope: "planning",
  import: "engine"
};

const manualTargetKeys: Record<string, { label: string; detail: string }> = {
  planning: { label: "manualTargetPlanning", detail: "manualPlanningDetail" },
  comfyui: { label: "manualTargetComfyui", detail: "manualComfyMissing" },
  blender: { label: "manualTargetBlender", detail: "manualBlenderMissing" },
  unreal: { label: "manualTargetUnreal", detail: "manualUnrealMissing" },
  godot: { label: "manualTargetGodot", detail: "manualGodotMissing" },
  generated: { label: "manualTargetGenerated", detail: "manualGeneratedDetail" }
};

// The console keeps only what the workbench does not have: asset review (which
// owns the approval manifest) and the production spec bundle. The other panels
// used to be duplicated here -- overview / tasks / build / visuals / gdd / dsl --
// as second copies of the shared implementations in `shared/panels/PlanPanels.tsx`.
// Those duplicates are gone: the workbench is the single place to read a plan,
// and the console is the place to act on it. The shared implementations were
// left untouched; only this entry point was removed.
const tabGroups: Array<{ labelKey: string; tabs: Array<[TabKey, string]> }> = [
  {
    labelKey: "tabGroupAssets",
    tabs: [
      ["review", "tabReview"],
      ["specs", "tabSpecs"]
    ]
  }
];

/**
 * `active` defaults to true so the console behaves as it always did when it is
 * rendered on its own -- which is how the component tests mount it. The shell
 * passes the real value: a view it keeps mounted after the operator switches
 * away is no longer the view a fresh handoff is addressed to.
 */
export function FlowConsole({
  active = true,
  focus = "review",
  reviewStage = "",
  journeyStep = "execute",
  onNavigateStep
}: {
  active?: boolean;
  focus?: "review" | "specs";
  reviewStage?: string;
  journeyStep?: "execute" | "review" | "qa";
  onNavigateStep?: (step: JourneyStepId) => void;
} = {}) {
  const { update, session: orchestrationSession } = useJourney();
  // Locale and theme are the provider's, not this view's. The console used to
  // own both and write `document.documentElement` itself -- correct while it was
  // its own document, wrong now that it renders inside the shell, where two
  // effects writing the same attribute is a race with no author.
  const { locale, theme, setLocale, setTheme } = useLocaleTheme();
  const project = useProject();
  const bindingKey = `${project.active?.project_id ?? ""}:${project.active?.plan_version ?? 0}`;
  const currentBinding = useRef(bindingKey);
  currentBinding.current = bindingKey;
  const [demoBinding, setDemoBinding] = useState("");
  const [assetBinding, setAssetBinding] = useState("");
  const [playtestBinding, setPlaytestBinding] = useState("");
  const [reviewBinding, setReviewBinding] = useState("");
  const [status, setStatus] = useState<StatusState>("idle");
  const setDemoStatus = useCallback((next: StatusState) => { if (demoBinding === currentBinding.current) setStatus(next); }, [demoBinding]);
  const setAssetStatus = useCallback((next: StatusState) => { if (assetBinding === currentBinding.current) setStatus(next); }, [assetBinding]);
  const setPlaytestStatus = useCallback((next: StatusState) => { if (playtestBinding === currentBinding.current) setStatus(next); }, [playtestBinding]);
  useEffect(() => setStatus("idle"), [bindingKey]);
  const [activeTab, setActiveTab] = useState<TabKey>(focus);
  const [pendingResume, setPendingResume] = useState<string | null>(null);
  const [pendingManualTarget, setPendingManualTarget] = useState<string | null>(null);
  const [orchestrationSessionLoading, setOrchestrationSessionLoading] = useState(false);
  const [reviewTarget, setReviewTarget] = useState(reviewStage);
  const [withAssets, setWithAssets] = useState(false);
  const [withVisuals, setWithVisuals] = useState(false);
  const [withGameplay, setWithGameplay] = useState(false);
  const [generateEffects, setGenerateEffects] = useState<string[] | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [assetWithAssets, setAssetWithAssets] = useState(true);
  const [assetWithVisuals, setAssetWithVisuals] = useState(true);
  const [assetEffects, setAssetEffects] = useState<string[] | null>(null);
  const [playtestRuns, setPlaytestRuns] = useState(3);
  const [playtestEffects, setPlaytestEffects] = useState<string[] | null>(null);
  const [evolutionRunning, setEvolutionRunning] = useState(false);
  const [evolutionVisited, setEvolutionVisited] = useState(journeyStep === "qa");
  /**
   * Which card of the plan rail is unfolded. The rail is four panels of input
   * and queues and a reader only ever works in one of them, so the other three
   * stay as title bars. Nothing is unmounted: the correction composer keeps
   * whatever was typed into it, and the run rail -- which owns the in-flight
   * jobs -- is not folded at all.
   */
  const [openPlanCard, setOpenPlanCard] = useState<PlanCardKey>("handoff");

  const t = useMemo(() => makeTranslator(locale, consoleI18n), [locale]);

  useEffect(() => {
    if (active) setActiveTab(focus);
    if (reviewStage) setReviewTarget(reviewStage);
  }, [active, focus, reviewStage]);

  useEffect(() => {
    setActiveTab(journeyStep === "qa" ? "specs" : "review");
    if (journeyStep === "qa") setEvolutionVisited(true);
  }, [journeyStep]);
  const { activityEntries, addActivity } = useActivityLog();
  const { enemyTuning, setEnemyTuningValue } = useEnemyTuning();
  const {
    currentPlan,
    currentReview,
    currentHandoff,
    reviewDecisions,
    setReviewDecisions,
    updateProductionSpecBundle,
    titleForPlan,
    renderHandoffTitle,
    loadPlanningHandoff
  } = usePlanningHandoff({ active, locale, t, addActivity, setStatus });
  useEffect(() => {
    if (!active || orchestrationSession) {
      setOrchestrationSessionLoading(false);
      return;
    }
    const orchestrationSessionId = readOrchestrationSessionId();
    if (!orchestrationSessionId) {
      setOrchestrationSessionLoading(false);
      return;
    }

    let cancelled = false;
    setOrchestrationSessionLoading(true);
    void getOrchestrationState(orchestrationSessionId, readOrchestrationEngine())
      .then((session) => {
        if (!cancelled && session.found && session.stages?.length) update({ session });
      })
      .catch(() => {
        // A missing or unreadable orchestration snapshot does not block the console.
      })
      .finally(() => {
        if (!cancelled) setOrchestrationSessionLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active, orchestrationSession, update]);
  const { manualTargetsPayload, loadManualTargets, fallbackManualTargets } = useManualTargets(currentPlan);
  const { specPreview, specPreviewError } = useSpecPreview(currentPlan, activeTab === "specs");
  const { request: specRegenRequest, regenerated, regenerating, regenError, regenerate, clear: clearRegen } =
    useSpecRegen(currentPlan);
  const { approvalManifestPath, onWriteApprovalManifest } = useApprovalManifest({
    currentPlan,
    review: currentReview,
    reviewDecisions,
    setStatus,
    addActivity,
    t,
    onBundleSynced: project.active ? () => { void projectStore.refresh(); } : updateProductionSpecBundle
  });

  const modeLabel = useCallback((mode: CorrectionMode) => t(correctionModeKeys[mode] || "modeGameplay"), [t]);

  /**
   * The three background jobs, each owning its own id and result. They sit at
   * the top of the component because everything below them reads what they
   * produce: the project a playtest measures, the session's node states, the
   * correction queue's scan. The `visitedPanels` contract (a view is never
   * unmounted, so an in-flight job keeps running) is why keeping this state
   * inside the component's hooks is safe and hoisting it to a provider is not.
   */
  const {
    jobId: pollJobId,
    result: localGenerateResult,
    cancelling: demoCancelling,
    cancel: cancelDemoJob,
    start: startDemoJob,
    reset: resetDemoJob
  } = useDemoJobPolling({
    setStatus: setDemoStatus,
    addActivity,
    doneLabel: t("generateDone"),
    failedLabel: t("generateFailed"),
    cancelledLabel: t("generateCancelled"),
    projectDirOnDone: true
  });

  const {
    jobId: pollAssetJobId,
    result: localAssetResult,
    cancelling: assetCancelling,
    cancel: cancelAssetJob,
    start: startAssetJob,
    reset: resetAssetJob
  } = useAssetJobPolling({
    setStatus: setAssetStatus,
    addActivity,
    doneLabel: t("assetExecutionDone"),
    failedLabel: t("assetExecutionFailed"),
    cancelledLabel: t("assetExecutionCancelled")
  });

  const {
    jobId: pollPlaytestJobId,
    result: localPlaytestResult,
    cancelling: playtestCancelling,
    cancel: cancelPlaytestRun,
    start: startPlaytestJob,
    reset: resetPlaytestJob
  } = usePlaytestJobPolling({
    setStatus: setPlaytestStatus,
    addActivity,
    doneLabel: t("playtestDone"),
    failedLabel: t("playtestFailed"),
    cancelledLabel: t("playtestCancelled")
  });

  const externalGenerate = currentWorkflowResult(project.active, project.jobs, "execute_demo") as ExecuteResult | undefined;
  const externalAssets = currentWorkflowResult(project.active, project.jobs, "execute_assets") as ExecuteResult | undefined;
  const externalPlaytestData = currentWorkflowResult(project.active, project.jobs, "playtest_godot_project");
  const externalPlaytest = externalPlaytestData && "aggregate" in externalPlaytestData ? { status: String(externalPlaytestData.status ?? "done"), report: externalPlaytestData as PlaytestReport, project_dir: String(externalPlaytestData.project_dir ?? "") } : externalPlaytestData as PlaytestResult | undefined;
  const externalEvolutionData = currentWorkflowResult(project.active, project.jobs, "run_evolution");
  const externalEvolutionReport = externalEvolutionData && "report" in externalEvolutionData ? externalEvolutionData.report : externalEvolutionData;
  const externalEvolution = externalEvolutionReport && typeof externalEvolutionReport === "object"
    && "iterations" in externalEvolutionReport && Array.isArray(externalEvolutionReport.iterations)
    ? externalEvolutionReport as import("../shared/types").EvolutionReport : undefined;
  const generateResult = externalGenerate ?? (demoBinding === bindingKey ? localGenerateResult : null);
  const assetResult = externalAssets ?? (assetBinding === bindingKey ? localAssetResult : null);
  const playtestResult = externalPlaytest ?? (playtestBinding === bindingKey ? localPlaytestResult : null);
  useEffect(() => {
    if (reviewBinding && reviewBinding !== bindingKey) { setGenerateEffects(null); setAssetEffects(null); setPlaytestEffects(null); setPendingResume(null); }
  }, [bindingKey, reviewBinding]);

  // Once a run settles, read back which nodes finished so the operator can
  // re-run one of them instead of the whole chain.
  const { state: sessionState } = useSessionState({
    sessionId: demoBinding === bindingKey ? sessionId : null,
    engine: usesGodotEngine(currentPlan) ? "godot" : "unreal",
    busy: Boolean(pollJobId)
  });

  // The project a playtest measures: whatever the last run produced, or the
  // session it belongs to. Without a directory there is nothing to play.
  const playtestProjectDir =
    playtestResult?.project_dir || generateResult?.project_dir || sessionState?.project_dir || "";

  const {
    mode: selectedCorrectionMode,
    setMode: setSelectedCorrectionMode,
    entries: correctionEntries,
    notes: correctionNotes,
    setNotes: setCorrectionNotes,
    scan: correctionScan,
    scanning: scanningCorrections,
    record: recordCorrection,
    runScan: scanCorrections
  } = useCorrections({
    projectDir: playtestProjectDir,
    hasPlan: Boolean(currentPlan),
    modeLabel,
    t,
    setStatus,
    addActivity
  });

  /**
   * How much is waiting on the operator right now: queued corrections plus
   * approvals the current orchestration pass is actually waiting on. The plan's
   * `requires_confirmation` flags describe future work, not a live approval.
   * This is the one number a folded
   * rail may never hide -- a confirmation nobody can see is a pipeline that
   * stops for no visible reason -- so it badges the collapsed title *and*
   * forces the gates card open while it is non-zero.
   */
  const activePipelineStageIds = new Set(currentPlan?.production_pipeline?.stages?.map((stage) => stage.id) ?? []);
  const pendingConfirmations = (orchestrationSession?.pending_confirmations ?? []).filter((stageId) => {
    const stage = orchestrationSession?.stages?.find((item) => item.stage_id === stageId);
    return activePipelineStageIds.has(stageId) && stage?.status === "awaiting_confirmation" && !stage.confirmed;
  });
  const pendingGates = correctionEntries.length + pendingConfirmations.length;
  const statusStep: JourneyStepId = pendingConfirmations.length
    ? "orchestrate"
    : pollPlaytestJobId || evolutionRunning
      ? "qa"
      : journeyStep;

  /** Exactly one card of the plan rail is open, plus the gates card when it has
   * something to say. See `openPlanCard` for why the other three stay folded. */
  const planCardOpen = (key: PlanCardKey) => openPlanCard === key || (key === "operator" && pendingGates > 0);

  /**
   * Toggling is not `onToggle`: a `<details>` fires that after the browser has
   * already changed `open`, which with React re-rendering from state means two
   * sources of truth fighting over one attribute. The card's openness is
   * derived from `openPlanCard`, and this is the only writer.
   */
  const togglePlanCard = (key: PlanCardKey) => setOpenPlanCard((current) => (current === key ? "handoff" : key));

  const recommendedManualTargetId = useCallback(() => {
    const mapped = correctionModeManualTargets[selectedCorrectionMode] || "planning";
    if (mapped === "engine") return usesGodotEngine(currentPlan) ? "godot" : "unreal";
    return mapped;
  }, [currentPlan, selectedCorrectionMode]);

  const manualTargetLabel = useCallback((target?: ManualCorrectionTarget) => t(manualTargetKeys[target?.id || "planning"]?.label || "manualTargetPlanning"), [t]);

  const manualTargetDetail = useCallback(
    (target?: ManualCorrectionTarget) => {
      const keys = manualTargetKeys[target?.id || "planning"] || manualTargetKeys.planning;
      if (target?.status === "ready" && target.id !== "planning" && target.id !== "generated") {
        const readyKey = `manual${target.id.charAt(0).toUpperCase()}${target.id.slice(1)}Ready`;
        return t(readyKey);
      }
      return target?.detail_key ? t(target.detail_key) : target?.detail || t(keys.detail);
    },
    [t]
  );

  const reviewPending = Object.values(reviewDecisions).filter((decision) => !decision || decision === "pending" || decision === "needs_revision").length;
  const qaStatus = specPreview?.executable_qa?.status || "";
  useEffect(() => update({ plan: currentPlan, executionStatus: status, reviewPending, qaStatus }), [currentPlan, qaStatus, reviewPending, status, update]);
const demoPhase = operationPhase({
    status,
    confirming: Boolean(generateEffects) || Boolean(pendingResume),
    hasPreview: Boolean(generateEffects),
    resumable: Boolean(sessionState?.failed?.length)
  });
  const demoReasonKey = !currentPlan ? "operationNeedsPlan" : operationReason(demoPhase);
  useEffect(() => {
    if (!active || activeTab !== "review" || !reviewTarget) return;
    const asset = document.getElementById(`review-asset-${reviewTarget}`);
    const gate = document.getElementById(`approval-${reviewTarget}`);
    (asset || gate)?.scrollIntoView?.({ block: "nearest" });
  }, [active, activeTab, reviewTarget]);
  const targets = manualTargetsPayload?.targets?.length ? manualTargetsPayload.targets : fallbackManualTargets();
  const recommendedTarget = targets.find((target) => target.id === recommendedManualTargetId()) || targets[0];
  const enemies = currentPlan?.gameplay_spec?.enemies || [];

  const openManualTarget = async (targetId: string) => {    if (targetId === "planning") {
      // Opened as a document of its own, so it reads locale and theme from the
      // shared localStorage key -- the same one this window just wrote. It used
      // to carry them across as `?locale=&theme=`, which was the last remaining
      // copy of the parameter-passing protocol the iframes needed.
      window.open("/workbench", "_blank", "noopener");
      addActivity(t("manualOpenStarted"), t("manualTargetPlanning"));
      return;
    }
    const target = targetId === "engine" ? recommendedManualTargetId() : targetId;
    // The backend gate refuses without confirmation. The dialog is the second
    // step; this click only names the process that would start.
    setPendingManualTarget(target);
  };

  const confirmManualTarget = async (target: string) => {
    try {
      const result = await openManualCorrectionTargetApi(target, selectedEngineVersion(currentPlan), true);
      const label = result.detail_key ? t(result.detail_key) : result.detail || result.status || "";
      if (result.status === "started" || result.status === "client_route") {
        addActivity(t("manualOpenStarted"), `${target}: ${result.target || label}`);
      } else {
        addActivity(t("manualOpenBlocked"), `${target}: ${label}`);
      }
    } catch (error) {
      addActivity(t("manualOpenBlocked"), String(error));
    } finally {
      void loadManualTargets();
    }
  };

  const onGenerateClick = async () => {
    setReviewBinding(bindingKey);
    if (!currentPlan) {
      addActivity(t("generateRequiresPlan"), t("openPlanningHint"));
      setStatus("error");
      return;
    }
    try {
      const preview = await previewExecute(
        currentPlan,
        usesGodotEngine(currentPlan) ? "godot" : "unreal",
        withAssets,
        withVisuals,
        withGameplay,
        enemyTuning,
        approvalManifestPath || "generated/asset-approval-manifest.yaml"
      );
      if (currentBinding.current !== bindingKey) return;
      setGenerateEffects(preview.planned_side_effects || []);
    } catch (error) {
      setStatus("error");
      addActivity(t("generateFailed"), String(error));
    }
  };

  const startGenerate = async (confirmedByUser: boolean, resumeFrom?: string) => {
    setDemoBinding(bindingKey);
    if (!currentPlan || !confirmedByUser) return;
    setGenerateEffects(null);
    resetDemoJob();
    setStatus("running");
    addActivity(
      resumeFrom ? t("reworkRunning") : t("generateRunning"),
      resumeFrom ? `${t("reworkFromLabel")}: ${resumeFrom}` : ""
    );
    try {
      // Only a resume reuses the session; a plain run starts a fresh one so
      // node-level rework can never inherit stale artifacts by accident.
      const started = await startExecute(
        currentPlan,
        usesGodotEngine(currentPlan) ? "godot" : "unreal",
        withAssets,
        withVisuals,
        withGameplay,
        enemyTuning,
        approvalManifestPath || "generated/asset-approval-manifest.yaml",
        { ...(resumeFrom ? { sessionId: sessionId || undefined, resumeFrom } : {}), confirmedByUser }
      );
      if (started.job_id) {
        startDemoJob(started.job_id);
        if (started.session_id) setSessionId(started.session_id);
      } else {
        setStatus("error");
        addActivity(t("generateFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("generateFailed"), String(error));
    }
  };

  const onPlaytestClick = async () => {
    setReviewBinding(bindingKey);
    if (!playtestProjectDir) {
      addActivity(t("playtestFailed"), t("playtestNeedsProject"));
      setStatus("error");
      return;
    }
    try {
      const preview = await previewPlaytest({
        project_dir: playtestProjectDir,
        runs: playtestRuns,
        goal_session_minutes: currentPlan?.gameplay_spec?.target_session_minutes
      });
      if (currentBinding.current !== bindingKey) return;
      setPlaytestEffects(preview.planned_side_effects || []);
    } catch (error) {
      setStatus("error");
      addActivity(t("playtestFailed"), String(error));
    }
  };

  const startPlaytestRun = async (confirmedByUser: boolean) => {
    setPlaytestBinding(bindingKey);
    if (!playtestProjectDir || !confirmedByUser) return;
    setPlaytestEffects(null);
    resetPlaytestJob();
    setStatus("running");
    addActivity(t("playtestRunning"), playtestProjectDir);
    try {
      const started = await startPlaytest({
        project_dir: playtestProjectDir,
        runs: playtestRuns,
        goal_session_minutes: currentPlan?.gameplay_spec?.target_session_minutes
      }, confirmedByUser);
      if (started.job_id) {
        startPlaytestJob(started.job_id);
      } else {
        setStatus("error");
        addActivity(t("playtestFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("playtestFailed"), String(error));
    }
  };

  const onAssetExecutionClick = async () => {
    setReviewBinding(bindingKey);
    if (!currentPlan) {
      addActivity(t("generateRequiresPlan"), t("openPlanningHint"));
      setStatus("error");
      return;
    }
    try {
      const preview = await previewAssetExecution(currentPlan, assetWithAssets, assetWithVisuals);
      if (currentBinding.current !== bindingKey) return;
      setAssetEffects(preview.planned_side_effects || []);
    } catch (error) {
      setStatus("error");
      addActivity(t("assetExecutionFailed"), String(error));
    }
  };

  const startAssetWorkers = async (confirmedByUser: boolean) => {
    setAssetBinding(bindingKey);
    if (!currentPlan || !confirmedByUser) return;
    setAssetEffects(null);
    resetAssetJob();
    setStatus("running");
    addActivity(t("assetExecutionRunning"), "");
    try {
      const started = await startAssetExecution(currentPlan, assetWithAssets, assetWithVisuals, confirmedByUser);
      if (started.job_id) {
        startAssetJob(started.job_id);
      } else {
        setStatus("error");
        addActivity(t("assetExecutionFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("assetExecutionFailed"), String(error));
    }
  };

  // Both metrics are computed from what this view holds. The console used to
  // also show `production_pipeline.current_stage` / `next_stage` and a strip of
  // the pipeline's stage rows -- plan-time values, written once when the plan
  // was authored, rendered as if they were run state. The board is the one
  // place that shows a stage's real status now; this view shows what it can
  // actually vouch for.
  const metrics = {
    reviewItems: String(currentReview?.items?.length || 0),
    blockedTasks: String((currentPlan?.task_breakdown?.tasks || []).filter((task) => task.status === "blocked").length)
  };

  return (
    <main className="shell" data-journey-step={journeyStep}>
      <WorkflowJobs />
      <header className="top-bar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">FA</span>
          <div>
            <p className="eyebrow">{t("productLabel")}</p>
            <h1>{t("brandName")}</h1>
          </div>
        </div>
        <div className="plan-headline">
          <div className="plan-headline-text">
            <p className="eyebrow">{t("statusLabel")}</p>
            <h2 id="plan-title">{currentPlan ? titleForPlan(currentPlan) : t("emptyTitle")}</h2>
          </div>
          <div className="status-chip" id="status-chip" data-status={status}>
            {t(status)}
          </div>
        </div>
        <div className="top-controls">
          <SegmentedControl
            label="Interface language"
            value={locale}
            options={[
              ["en", "EN"],
              ["zh-CN", "\u4e2d\u6587"]
            ]}
            onChange={(value) => {
              setLocale(value as Locale);
              addActivity(t("switchedLocale"), value);
            }}
          />
          <SegmentedControl
            label="Theme"
            value={theme}
            options={[
              ["dark", t("themeDark")],
              ["light", t("themeLight")]
            ]}
            onChange={(value) => setTheme(value as Theme)}
            className="theme-switch"
            buttonClassName="theme-option"
          />
        </div>
      </header>

      {(pendingGates > 0 || pollJobId || pollAssetJobId || pollPlaytestJobId || evolutionRunning || status === "error") ? (
        <div className="journey-status-bar" role="status" data-status={status === "error" ? "error" : pollJobId || pollAssetJobId || pollPlaytestJobId || evolutionRunning ? "running" : "awaiting_confirmation"}>
          {onNavigateStep ? (
            <button
              className="journey-status-link"
              type="button"
              onClick={() => onNavigateStep(statusStep)}
              aria-label={`${t(JOURNEY_STEP_KEYS[statusStep])}: ${t("journeyNext")}`}
            >
              {t(JOURNEY_STEP_KEYS[statusStep])}
            </button>
          ) : <strong>{t(JOURNEY_STEP_KEYS[statusStep])}</strong>}
          <span>
            {pendingGates > 0
              ? t("gatesPending")
              : pollJobId || pollAssetJobId || pollPlaytestJobId || evolutionRunning
                ? t("operationRunning")
                : t("operationFailed")}
          </span>
          {pendingGates > 0 ? <span className="journey-status-count">{pendingGates}</span> : null}
        </div>
      ) : null}

      <section className="workspace" aria-label={t("cockpitLabel")}>
        {journeyStep === "execute" ? <aside className="side-rail plan-rail" aria-label={t("railPlanTitle")}>
          <p className="rail-title">{t("railPlanTitle")}</p>

          <details className="rail-fold" data-panel="handoff" aria-label={t("handoffTitle")} open={planCardOpen("handoff")}>
            <summary onClick={(event) => { event.preventDefault(); togglePlanCard("handoff"); }}>
              <h2>{t("handoffTitle")}</h2>
              <span className="handoff-chip" id="handoff-state">
                {currentHandoff?.plan ? t("handoffLoadedShort") : t("waitingForPlan")}
              </span>
            </summary>
            <div className="rail-card-body">
            <div id="handoff-summary" className="handoff-summary">
              {currentHandoff?.invalid ? (
                <p>{t("invalidHandoff")}</p>
              ) : currentHandoff?.plan ? (
                <>
                  <strong>{renderHandoffTitle(currentHandoff)}</strong>
                  <div className="handoff-meta">
                    <span>
                      {t("session")}: {currentHandoff.plan.gameplay_spec?.target_session_minutes || "-"} {t("minutes")}
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <p>{t("handoffEmpty")}</p>
                  <p>{t("openPlanningHint")}</p>
                </>
              )}
            </div>
            <div className="handoff-actions">
              <button className="primary-action" type="button" id="load-handoff-button" onClick={() => loadPlanningHandoff()}>
                {t("loadHandoff")}
              </button>
            </div>
            <p className="ui-hint">{t("handoffHint")}</p>
            </div>
          </details>

          <details className="rail-fold" data-panel="correction" aria-label="Correction queue" open={planCardOpen("correction")}>
            <summary onClick={(event) => { event.preventDefault(); togglePlanCard("correction"); }}>
              <h2>{t("correctionTitle")}</h2>
            </summary>
            <div className="rail-card-body">
            <div className="mode-grid" role="group" aria-label="Correction mode">
              {(["gameplay", "visuals", "scope", "import"] as CorrectionMode[]).map((mode) => (
                <button
                  className={`mode-option ${selectedCorrectionMode === mode ? "active" : ""}`}
                  type="button"
                  data-correction-mode={mode}
                  key={mode}
                  onClick={() => setSelectedCorrectionMode(mode)}
                >
                  {modeLabel(mode)}
                </button>
              ))}
            </div>
            <label className="field-label" htmlFor="correction-notes">
              {t("correctionNotes")}
            </label>
            <textarea
              id="correction-notes"
              rows={5}
              placeholder={t("correctionPlaceholder")}
              value={correctionNotes}
              onChange={(event) => setCorrectionNotes(event.target.value)}
            />
            <button className="secondary-action" type="button" id="record-correction-button" onClick={recordCorrection}>
              {t("recordCorrection")}
            </button>
            </div>
          </details>

          <details className="rail-fold" data-panel="manual-correction" aria-label="Manual correction tools" open={planCardOpen("manual-correction")}>
            <summary onClick={(event) => { event.preventDefault(); togglePlanCard("manual-correction"); }}>
              <h2>{t("manualCorrectionTitle")}</h2>
            </summary>
            <div className="rail-card-body">
            <p className="ui-hint">{t("manualCorrectionHint")}</p>
            <div className="manual-summary-row">
              <span id="manual-tool-summary">
                {t("manualRecommended")}: {manualTargetLabel(recommendedTarget)} / {modeLabel(selectedCorrectionMode)}
              </span>
              <button
                className="secondary-action compact-action"
                type="button"
                id="open-recommended-tool-button"
                disabled={!recommendedTarget?.openable}
                onClick={() => void openManualTarget(recommendedTarget?.id || recommendedManualTargetId())}
              >
                {t("manualOpenRecommended")}
              </button>
            </div>
            <div id="manual-tool-grid" className="manual-tool-list">
              {targets.map((target) => (
                <article
                  className="manual-tool-row"
                  data-state={target.status || "unavailable"}
                  data-recommended={target.id === recommendedManualTargetId() ? "true" : undefined}
                  key={target.id}
                >
                  <div className="manual-tool-name">
                    <h3>{manualTargetLabel(target)}</h3>
                    {target.id === recommendedManualTargetId() ? (
                      <span className="task-pill" data-status="ready">{t("manualRecommended")}</span>
                    ) : null}
                  </div>
                  <div className="manual-tool-side">
                    <span className="task-pill" data-status={target.status}>{manualStatusLabel(target.status, t)}</span>
                    <button className="mini-action" type="button" data-manual-target={target.id} disabled={!target.openable} onClick={() => void openManualTarget(target.id)}>
                      {t("manualOpen")}
                    </button>
                  </div>
                  <p>{manualTargetDetail(target)}</p>
                </article>
              ))}
            </div>
            <div className="correction-scan">
              <button
                className="secondary-action"
                type="button"
                id="scan-corrections-button"
                disabled={!playtestProjectDir || scanningCorrections}
                onClick={() => void scanCorrections()}
              >
                {scanningCorrections ? t("correctionScanning") : t("correctionScan")}
              </button>
              {correctionScan ? <CorrectionReportCard report={correctionScan} t={t} /> : null}
            </div>
            </div>
          </details>

          <details className="rail-fold" data-panel="operator" aria-label="Execution confirmations" aria-busy={orchestrationSessionLoading} open={planCardOpen("operator")}>
            <summary onClick={(event) => { event.preventDefault(); togglePlanCard("operator"); }}>
              <h2>{t("gatesTitle")}</h2>
              {pendingGates > 0 ? (
                <span className="gate-count" id="gate-count" aria-label={t("gatesPending")}>
                  {pendingGates}
                </span>
              ) : null}
            </summary>
            <div className="rail-card-body">
            <div id="gate-summary" className="gate-stack">
              {currentPlan ? (
                <>
                  {correctionEntries.slice(0, 3).map((entry) => (
                    <GateItem key={entry.createdAt} title={`${t("correctionPending")} · ${modeLabel(entry.mode)}`} detail={entry.notes} />
                  ))}
                  {pendingConfirmations.slice(0, 6).map((stageId) => {
                    const stage = orchestrationSession?.stages?.find((item) => item.stage_id === stageId);
                    return (
                      <GateItem
                        key={stageId}
                        title={stage?.title || stageId || t("confirmation")}
                        detail={stage?.detail || stage?.status || ""}
                      />
                    );
                  })}
                </>
              ) : (
                <>
                  <GateItem title={t("defaultGateVisuals")} detail={t("waitingForPlan")} />
                  <GateItem title={t("defaultGateMeshes")} detail={t("waitingForPlan")} />
                  <GateItem title={t("defaultGateUnreal")} detail={t("waitingForPlan")} />
                </>
              )}
            </div>
            </div>
          </details>

        </aside> : null}

        <section className="center-pane" aria-label="Plan inspection">
          <section className="insight-row" aria-label="Plan metrics">
            <Metric label={t("reviewItems")} value={metrics.reviewItems} id="metric-review-items" />
            <Metric label={t("blockedTasks")} value={metrics.blockedTasks} id="metric-blocked-tasks" />
          </section>

          <nav className="tabs" aria-label="Plan views">
            {tabGroups.map((group) => (
              <div className="tab-group" key={group.labelKey}>
                <span className="tab-group-label">{t(group.labelKey)}</span>
                <div className="tab-group-buttons">
                  {group.tabs.map(([tab, label]) => (
                    <button className={`tab ${activeTab === tab ? "active" : ""}`} type="button" data-tab={tab} key={tab} onClick={() => setActiveTab(tab)}>
                      {t(label)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </nav>

          <section className="content-frame">
            <Panel tab="review" activeTab={activeTab}>
              <ReviewPanel
                review={currentReview}
                locale={locale}
                decisions={reviewDecisions}
                setDecision={(assetId, decision) => {
                  setReviewDecisions((decisions) => ({ ...decisions, [assetId]: decision }));
                  addActivity(t("reviewDecision"), `${assetId}: ${statusLabel(decision, t)}`);
                }}
                manifestPath={approvalManifestPath}
                onWriteManifest={() => void onWriteApprovalManifest()}
                t={t}
              />
            </Panel>
            <Panel tab="specs" activeTab={activeTab}>
              {evolutionVisited ? <div hidden={journeyStep !== "qa"}>
                <EvolutionPanel externalReport={externalEvolution} plan={currentPlan}
                  binding={project.active ? { project_id: project.active.project_id, plan_version: project.active.plan_version } : undefined}
                  t={t} active={active && journeyStep === "qa"}
                  onAdoptBundle={updateProductionSpecBundle} onRunningChange={setEvolutionRunning} />
              </div> : null}
              <SpecBundlePanel
                bundle={currentPlan?.production_spec_bundle}
                spec={currentPlan?.gameplay_spec}
                locale={locale}
                preview={specPreview}
                error={specPreviewError}
                t={t}
              />
              {currentPlan?.production_spec_bundle ? (
                <SpecRegenPanel
                  request={specRegenRequest}
                  locale={locale}
                  regenerated={regenerated}
                  regenerating={regenerating}
                  error={regenError}
                  baseline={currentPlan?.gameplay_spec}
                  onRegenerate={() => void regenerate()}
                  onClear={clearRegen}
                  t={t}
                />
              ) : null}
            </Panel>
          </section>

        </section>

        {journeyStep !== "review" ? <aside className="side-rail run-rail" aria-label={t("railRunTitle")}>
          <p className="rail-title">{t("railRunTitle")}</p>

          {journeyStep === "execute" ? <section className="rail-card" data-panel="run" aria-label="Run approved asset workers">
            <div className="pane-section-header">
              <h2>{t("assetExecutionTitle")}</h2>
            </div>
            <p className="ui-hint">{t("assetExecutionHint")}</p>
            <div className="generate-options">
              <label>
                <input type="checkbox" id="asset-with-assets" checked={assetWithAssets} onChange={(event) => setAssetWithAssets(event.target.checked)} /> <span>{t("generateWithAssets")}</span>
              </label>
              <label>
                <input type="checkbox" id="asset-with-visuals" checked={assetWithVisuals} onChange={(event) => setAssetWithVisuals(event.target.checked)} /> <span>{t("generateWithVisuals")}</span>
              </label>
            </div>
            <button className="secondary-action" type="button" id="asset-execute-button" disabled={status === "running" || !currentPlan} aria-describedby="asset-phase-reason" onClick={() => void onAssetExecutionClick()}>
              {t("assetExecutionButton")}
            </button>
            <p id="asset-phase-reason">{!currentPlan ? t("operationNeedsPlan") : status === "running" ? t("operationCancelable") : assetEffects ? t("operationConfirming") : t("operationIdle")}</p>
            {pollAssetJobId ? (
              <button className="secondary-action" type="button" id="asset-execute-stop" disabled={assetCancelling} onClick={() => void cancelAssetJob()}>
                {assetCancelling ? t("stoppingJob") : t("stopJob")}
              </button>
            ) : null}
            {assetEffects ? (
              <div id="asset-execute-confirm" className="generate-confirm">
                <strong>{t("assetConfirmTitle")}</strong>
                <p>{t("assetConfirmIntro")}</p>
                <ul>{assetEffects.map((effect) => <li key={effect}>{effect}</li>)}</ul>
                <div className="handoff-actions">
                  <button className="primary-action" type="button" id="asset-execute-proceed" value="approved" onClick={(event) => void startAssetWorkers(event.currentTarget.value === "approved")}>
                    {t("assetConfirmProceed")}
                  </button>
                  <button className="ghost-action" type="button" id="asset-execute-cancel" onClick={() => setAssetEffects(null)}>
                    {t("generateConfirmCancel")}
                  </button>
                </div>
              </div>
            ) : null}
            <div id="asset-execute-stages" className="generate-stages">
              {assetResult?.stages?.map((stage) => <ExecutionStageCard key={stage.name} stage={stage} t={t} />)}
            </div>
          </section> : null}

          <section className="rail-card" data-panel="generate" aria-label={journeyStep === "qa" ? "Playtest and recovery" : "Generate playable demo"}>
            <div className="pane-section-header">
              <h2>{journeyStep === "qa" ? t("playtestTitle") : t("generateTitle")}</h2>
            </div>
            {journeyStep === "execute" ? <>
            <p className="ui-hint">{t("generateHint")}</p>
            <div className="generate-options">
              <label>
                <input type="checkbox" id="generate-with-assets" checked={withAssets} onChange={(event) => setWithAssets(event.target.checked)} /> <span>{t("generateWithAssets")}</span>
              </label>
              <label>
                <input type="checkbox" id="generate-with-visuals" checked={withVisuals} onChange={(event) => setWithVisuals(event.target.checked)} /> <span>{t("generateWithVisuals")}</span>
              </label>
              <label>
                <input type="checkbox" id="generate-with-gameplay" checked={withGameplay} onChange={(event) => setWithGameplay(event.target.checked)} /> <span>{t("generateWithGameplay")}</span>
              </label>
            </div>
            {withGameplay ? (
              <div className="enemy-tuning-panel">
                <div>
                  <strong>{t("enemyPressureTitle")}</strong>
                  <p>{t("enemyPressureHint")}</p>
                </div>
                <div className="enemy-roster">
                  {enemies.length ? enemies.map((enemy, index) => (
                    <span className="enemy-chip" key={`${enemy.name || "enemy"}-${index}`}>
                      {enemy.name || t("enemyFallbackName")} / {enemy.behavior || "patrol"} x{enemy.count || 1}
                    </span>
                  )) : <span className="enemy-chip">{t("enemyRosterEmpty")}</span>}
                </div>
                <div className="tuning-grid">
                  {(
                    [
                      ["enemy_count_multiplier", "enemyCountMultiplier", 0, 3],
                      ["move_speed_multiplier", "enemySpeedMultiplier", 0.25, 3],
                      ["detection_radius_multiplier", "enemyDetectionMultiplier", 0.25, 3],
                      ["patrol_radius_multiplier", "enemyPatrolMultiplier", 0.25, 3],
                      ["ranged_interval_multiplier", "enemyRangedIntervalMultiplier", 0.25, 3]
                    ] as Array<[keyof EnemyPressureTuning, string, number, number]>
                  ).map(([key, labelKey, min, max]) => (
                    <label className="tuning-field" key={key}>
                      <span>{t(labelKey)}</span>
                      <input
                        type="number"
                        min={min}
                        max={max}
                        step="0.05"
                        value={enemyTuning[key]}
                        onChange={(event) => setEnemyTuningValue(key, Number(event.target.value))}
                      />
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
            <StatusBadge status={demoPhase} label={t(operationReason(demoPhase))} />
            <button className="primary-action" type="button" id="generate-demo-button" disabled={status === "running" || !currentPlan} aria-describedby="generate-phase-reason" onClick={() => void onGenerateClick()}>
              {t("generateButton")}
            </button>
            <p id="generate-phase-reason">{t(demoReasonKey)}</p>
            {pollJobId ? (
              <button className="secondary-action" type="button" id="generate-stop" disabled={demoCancelling} onClick={() => void cancelDemoJob()}>
                {demoCancelling ? t("stoppingJob") : t("stopJob")}
              </button>
            ) : null}
            {generateEffects ? (
              <div id="generate-confirm" className="generate-confirm">
                <strong>{t("generateConfirmTitle")}</strong>
                <p>{t("generateConfirmIntro")}</p>
                <ul>{generateEffects.map((effect) => <li key={effect}>{effect}</li>)}</ul>
                <div className="handoff-actions">
                  <button className="primary-action" type="button" id="generate-proceed" value="approved" onClick={(event) => void startGenerate(event.currentTarget.value === "approved")}>
                    {t("generateConfirmProceed")}
                  </button>
                  <button className="ghost-action" type="button" id="generate-cancel" onClick={() => setGenerateEffects(null)}>
                    {t("generateConfirmCancel")}
                  </button>
                </div>
              </div>
            ) : null}
            <div id="generate-stages" className="generate-stages">
              {generateResult?.stages?.map((stage) => <ExecutionStageCard key={stage.name} stage={stage} t={t} />)}
              {generateResult?.project_dir ? (
                <p className="ui-hint">
                  {t("generateArtifact")}: <code>{generateResult.project_dir}</code>
                </p>
              ) : null}
            </div>
            </> : null}
            {sessionId && sessionState?.found ? (
              <div className="rework-panel" id="rework-panel">
                <div className="pane-section-header">
                  <h3>{t("reworkTitle")}</h3>
                </div>
                <p className="ui-hint">{t("reworkHint")}</p>
                <p className="ui-hint">
                  {t("reworkSession")}: <code>{sessionId}</code>
                </p>
                <ul className="rework-list">
                  {(sessionState?.stages || []).map((stage) => (
                    <li key={stage.name} className="rework-item" data-status={stage.status || "unknown"}>
                      <span className="rework-name">{stage.name}</span>
                      <span className="rework-status">{stage.status}</span>
                      {stage.status === "failed" ? (
                        <div className="recovery-actions" aria-label={t("recoveryTitle")}>
                          <a href="#activity-drawer">{t("recoveryLogs")}</a>
                          <a href="#correction-notes">{t("recoveryEditInput")}</a>
                          <button className="ghost-action" type="button" disabled={status === "running" || !stage.name} onClick={() => setPendingResume(stage.name || null)}>{t("reworkResume")}</button>
                        </div>
                      ) : null}
                      <span id={`rework-reason-${stage.name}`}>{stage.status === "failed" ? t("operationResumable") : t("operationIdle")}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="playtest-panel" id="playtest-panel">
              <div className="pane-section-header">
                <h3>{t("playtestTitle")}</h3>
              </div>
              <p className="ui-hint">{t("playtestHint")}</p>
              {playtestProjectDir ? (
                <p className="ui-hint">
                  {t("playtestProject")}: <code>{playtestProjectDir}</code>
                </p>
              ) : (
                <p className="ui-hint">{t("playtestNeedsProject")}</p>
              )}
              <label className="playtest-field">
                <span>{t("playtestRunsLabel")}</span>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={playtestRuns}
                  onChange={(event) => setPlaytestRuns(Number(event.target.value))}
                />
              </label>
              <button
                className="primary-action"
                type="button"
                id="playtest-run-button"
                disabled={status === "running" || !playtestProjectDir}
                onClick={() => void onPlaytestClick()}
              >
                {t("playtestRun")}
              </button>
              {pollPlaytestJobId ? (
                <button className="secondary-action" type="button" id="playtest-stop" disabled={playtestCancelling} onClick={() => void cancelPlaytestRun()}>
                  {playtestCancelling ? t("stoppingJob") : t("stopJob")}
                </button>
              ) : null}
              {playtestEffects ? (
                <PlaytestConfirmBlock effects={playtestEffects} t={t} onProceed={(confirmedByUser) => void startPlaytestRun(confirmedByUser)} onCancel={() => setPlaytestEffects(null)} />
              ) : null}
              {playtestResult?.report ? (
                <PlaytestReportCard report={playtestResult.report} t={t} onResume={(stage) => setPendingResume(stage)} />
              ) : null}
            </div>
          </section>

          <section className="rail-card activity-card" id="activity-drawer" aria-label="Activity log">
            <div className="activity-head">
              <strong>{t("activityTitle")}</strong>
              <span id="activity-count">{activityEntries.length}</span>
            </div>
            <LogBlock title={t("activityTitle")} lines={activityEntries.map((entry) => `${entry.time} ${entry.label}: ${entry.message}`)} />
            <ol id="activity-log" className="activity-log">
              {activityEntries.map((entry, index) => (
                <li key={`${entry.time}-${index}`}>
                  <span>{entry.time}</span>
                  <div>
                    <strong>{entry.label}</strong>
                    <br />
                    {entry.message}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </aside> : null}
      </section>


      <ConfirmDialog
        open={Boolean(pendingResume)}
        title={t("reworkResume")}
        body={t("reworkConfirm", { stage: pendingResume || "" })}
        confirmLabel={t("reworkResume")}
        cancelLabel={t("generateConfirmCancel")}
        onCancel={() => setPendingResume(null)}
        onConfirm={(confirmedByUser) => { const stage = pendingResume; setPendingResume(null); if (stage) void startGenerate(confirmedByUser, stage); }}
      />
      <ConfirmDialog
        open={Boolean(pendingManualTarget)}
        title={t("manualOpen")}
        body={t("manualOpenConfirm", { target: t(manualTargetKeys[pendingManualTarget || ""]?.label || "manualTargetPlanning") })}
        confirmLabel={t("manualOpen")}
        cancelLabel={t("generateConfirmCancel")}
        onCancel={() => {
          const target = pendingManualTarget;
          setPendingManualTarget(null);
          if (target) addActivity(t("manualOpenCancelled"), target);
        }}
        onConfirm={() => {
          const target = pendingManualTarget;
          setPendingManualTarget(null);
          if (target) void confirmManualTarget(target);
        }}
      />
    </main>
  );
}

// Exported so the stage rendering (including the logs list) can be unit tested
// without mounting the whole console.
/**
 * What a measured playtest found.
 *
 * The verdict badge shows the *report* status, which is deliberately not the
 * job status: a run that measured a failure still finished. Every finding
 * carries the rework target the board understands, so "this is broken" and
 * "resume from here" stay one click apart.
 */
import { AssetList, Metric, Panel, SegmentedControl, manualStatusLabel } from "./FlowConsole.parts";
import { ExecutionStageCard } from "./executionStage/ExecutionStageCard";
import { CorrectionReportCard } from "./correction/CorrectionReportCard";
import { PlaytestConfirmBlock } from "./playtest/PlaytestConfirmBlock";
import { PlaytestReportCard } from "./playtest/PlaytestReportCard";
import type { TabKey } from "./FlowConsole.parts";
